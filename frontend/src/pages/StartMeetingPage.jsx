import { useState, useRef, useEffect, useMemo } from 'react';
import {
  Camera,
  Mic,
  CheckCircle,
  AlertCircle,
  Loader2,
  MicOff,
  Users,
  Search,
  Activity,
  StopCircle,
  Play,
  RefreshCw
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import faceService from '../services/faceService';
import meetingService from '../services/meetingService';
import audioService from '../services/audioService';
import InlineRegistrationCard from '../components/Dashboard/InlineRegistrationCard';

export default function StartMeetingPage() {
  // Status: 'waiting', 'recording', 'processing'
  const [pipelineStatus, setPipelineStatus] = useState('waiting');
  const [error, setError] = useState(null);
  const [recognitionError, setRecognitionError] = useState(null);
  const [reviewData, setReviewData] = useState({ transcript: '', summary: '', audio_path: '' });
  const [pendingMeeting, setPendingMeeting] = useState(null);
  const [isSavingMeeting, setIsSavingMeeting] = useState(false);
  const [recognitionPaused, setRecognitionPaused] = useState(false);
  const [capturedImage, setCapturedImage] = useState(null);
  const [voiceActive, setVoiceActive] = useState(false);
  const [registrationInputs, setRegistrationInputs] = useState({});
  const [registeringIds, setRegisteringIds] = useState({});
  const [refreshingDetection, setRefreshingDetection] = useState(false);
  const [refreshToast, setRefreshToast] = useState(null);
  const [participants, setParticipants] = useState([]);
  const [lockedParticipants, setLockedParticipants] = useState([]);
  const [detectedFaces, setDetectedFaces] = useState([]);
  const [relatedMeetings, setRelatedMeetings] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [lastSavedAt, setLastSavedAt] = useState(null);
  const [lastSavedMeeting, setLastSavedMeeting] = useState(null);
  const [videoSize, setVideoSize] = useState({ width: 1280, height: 720 });
  const [expandedMeetingId, setExpandedMeetingId] = useState(null);

  // Refs for tracking background loops without triggering unneeded re-renders
  const loopRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const silenceTimeoutRef = useRef(null);
  const audioStreamRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const isRecognizingRef = useRef(false);
  const lastRecognitionAtRef = useRef(0);
  const pipelineStatusRef = useRef('waiting');
  const recognitionErrorRef = useRef(null);
  const participantsRef = useRef([]);
  const lockedParticipantsRef = useRef([]);
  const pendingMeetingRef = useRef(null);
  const faceMapRef = useRef(new Map());
  const recordingStartRef = useRef(null);
  const searchTimeoutRef = useRef(null);
  const recognitionPausedRef = useRef(false);
  const refreshingRef = useRef(false);

  const MIN_AUDIO_BYTES = 5120;
  const DETECTION_INTERVAL_MS = 500;
  const ACTIVE_GRACE_MS = 3500;
  const AUTO_STOP_SILENCE_MS = 12000;

  useEffect(() => { pipelineStatusRef.current = pipelineStatus; }, [pipelineStatus]);
  useEffect(() => { recognitionErrorRef.current = recognitionError; }, [recognitionError]);
  useEffect(() => { participantsRef.current = participants; }, [participants]);
  useEffect(() => { lockedParticipantsRef.current = lockedParticipants; }, [lockedParticipants]);
  useEffect(() => { pendingMeetingRef.current = pendingMeeting; }, [pendingMeeting]);
  useEffect(() => { recognitionPausedRef.current = recognitionPaused; }, [recognitionPaused]);
  useEffect(() => { refreshingRef.current = refreshingDetection; }, [refreshingDetection]);

  // Mount-only effect – NEVER re-runs when pipelineStatus changes.
  useEffect(() => {
    setupAudioPipeline();
    loopRef.current = setInterval(pollFaceRecognition, DETECTION_INTERVAL_MS);

    return () => {
      if (loopRef.current) clearInterval(loopRef.current);
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      if (audioStreamRef.current) {
        audioStreamRef.current.getTracks().forEach(t => t.stop());
      }
      if (silenceTimeoutRef.current) clearTimeout(silenceTimeoutRef.current);
      if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
    };
  }, []);

  useEffect(() => {
    if (pipelineStatus !== 'recording') {
      recordingStartRef.current = null;
      setRecordingSeconds(0);
      return;
    }
    recordingStartRef.current = Date.now();
    const timer = setInterval(() => {
      if (!recordingStartRef.current) return;
      const elapsed = Math.floor((Date.now() - recordingStartRef.current) / 1000);
      setRecordingSeconds(elapsed);
    }, 1000);
    return () => clearInterval(timer);
  }, [pipelineStatus]);

  const participantKey = useMemo(() => {
    const ids = participants.map(p => p.person_id || p.name).filter(Boolean).sort();
    return ids.join('|');
  }, [participants]);

  const parseSummarySections = (rawSummary) => {
    const summary = [];
    const actions = [];
    let section = 'summary';

    (rawSummary || '').split('\n').forEach((line) => {
      const trimmed = line.trim();
      if (!trimmed) return;
      const lower = trimmed.toLowerCase();
      if (lower.startsWith('meeting summary')) {
        section = 'summary';
        return;
      }
      if (lower.startsWith('action items')) {
        section = 'actions';
        return;
      }
      if (/^[-*•\s]+/.test(trimmed)) {
        const cleaned = trimmed.replace(/^[-*•\s]+/, '').trim();
        if (!cleaned) return;
        if (section === 'actions') actions.push(cleaned);
        else summary.push(cleaned);
      }
    });

    if (!summary.length && rawSummary) {
      rawSummary
        .split('\n')
        .map(line => line.replace(/^[-*•\s]+/, '').trim())
        .filter(Boolean)
        .forEach(line => summary.push(line));
    }

    const cleanedActions = actions.filter(item => item.toLowerCase() !== 'none');
    return { summary, actions: cleanedActions };
  };

  const summarySections = useMemo(() => parseSummarySections(reviewData.summary), [reviewData.summary]);

  useEffect(() => {
    if (!participantKey) {
      setRelatedMeetings([]);
      return;
    }
    if (pipelineStatus === 'processing') return;
    loadRelatedMeetings(participants);
  }, [participantKey, pipelineStatus]);

  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
    searchTimeoutRef.current = setTimeout(async () => {
      try {
        setSearching(true);
        const response = await meetingService.searchMeetings(searchQuery.trim());
        const meetings = unwrapMeetings(response);
        setSearchResults(meetings);
      } catch (err) {
        setSearchResults([]);
        setError(err?.error || 'Meeting search failed');
      } finally {
        setSearching(false);
      }
    }, 350);
  }, [searchQuery]);

  useEffect(() => {
    if (!refreshToast) return;
    const timeout = setTimeout(() => setRefreshToast(null), 3000);
    return () => clearTimeout(timeout);
  }, [refreshToast]);

  const pendingRegistrations = useMemo(
    () => detectedFaces.filter(face => face.unknown),
    [detectedFaces]
  );

  useEffect(() => {
    const activeIds = new Set(pendingRegistrations.map(face => String(face.id)));

    setRegistrationInputs((prev) => {
      const next = {};
      Object.entries(prev).forEach(([id, value]) => {
        if (activeIds.has(id)) next[id] = value;
      });
      return next;
    });

    setRegisteringIds((prev) => {
      const next = {};
      Object.entries(prev).forEach(([id, value]) => {
        if (activeIds.has(id) && value) next[id] = value;
      });
      return next;
    });
  }, [pendingRegistrations]);

  const formatTimer = (seconds) => {
    const mins = String(Math.floor(seconds / 60)).padStart(2, '0');
    const secs = String(seconds % 60).padStart(2, '0');
    return `${mins}:${secs}`;
  };

  const buildParticipantKey = (list) => {
    return list
      .map(p => p.person_id || p.name || 'unknown')
      .map(String)
      .sort()
      .join('|');
  };

  const unwrapMeetings = (response) => {
    if (!response) return [];
    if (Array.isArray(response)) return response;
    if (Array.isArray(response.meetings)) return response.meetings;
    if (Array.isArray(response.data)) return response.data;
    if (Array.isArray(response.results)) return response.results;
    return [];
  };

  const getUniqueNames = (names) => {
    if (!Array.isArray(names)) return [];
    const seen = new Set();
    const unique = [];
    names.forEach((name) => {
      const cleaned = String(name || '').trim();
      if (!cleaned) return;
      const key = cleaned.toLowerCase();
      if (seen.has(key)) return;
      seen.add(key);
      unique.push(cleaned);
    });
    return unique;
  };

  const splitIntoPoints = (text) => {
    if (!text) return [];
    const rawLines = String(text).split(/\r?\n/).map(line => line.trim()).filter(Boolean);
    if (rawLines.length > 1) return rawLines;

    const normalized = String(text).replace(/\s+/g, ' ').trim();
    if (!normalized) return [];

    const matches = normalized.match(/[^.!?]+[.!?]*/g) || [];
    const sentences = matches.map(segment => segment.trim()).filter(Boolean);
    return sentences.length ? sentences : [normalized];
  };

  const computeMeetingScore = (meeting, participantIds, participantNames) => {
    const meetingIds = meeting?.participant_ids || meeting?.participants || (meeting?.person_id ? [meeting.person_id] : []);
    const meetingNames = meeting?.participant_names || meeting?.participants_names || (meeting?.person_name ? [meeting.person_name] : []);
    const idSet = new Set(meetingIds.map(String));
    const nameSet = new Set(meetingNames.map(name => String(name).toLowerCase()));
    let score = 0;
    participantIds.forEach(id => {
      if (idSet.has(String(id))) score += 2;
    });
    participantNames.forEach(name => {
      if (nameSet.has(String(name).toLowerCase())) score += 1;
    });
    if (participantIds.length && participantIds.every(id => idSet.has(String(id)))) score += 5;
    return score;
  };

  const normalizeFaces = (response) => {
    if (!response) return [];
    const rawFaces = Array.isArray(response.faces)
      ? response.faces
      : Array.isArray(response.people)
        ? response.people
        : Array.isArray(response.results)
          ? response.results
          : (response.name || response.person_id || response.requires_registration ? [response] : []);

    return rawFaces.map((face, index) => {
      const personId = face.person_id ?? face.personId ?? face.id ?? null;
      const name = face.name || face.person_name || face.personName || (face.requires_registration ? 'Unregistered' : 'Unknown');
      const requiresRegistration = Boolean(face.requires_registration || face.needs_registration);
      const unknown = requiresRegistration || !personId || name === 'Unknown' || name === 'Unregistered';
      const box = face.box || face.bbox || face.bounding_box || face.rect || (face.left != null ? {
        left: face.left,
        top: face.top,
        right: face.right,
        bottom: face.bottom
      } : null);

      return {
        id: face.face_id ?? face.track_id ?? personId ?? `${name}-${index}`,
        name,
        person_id: personId,
        confidence: face.confidence ?? face.score ?? face.similarity ?? null,
        box,
        requires_registration: requiresRegistration,
        unknown,
        last_meeting: face.last_meeting || face.lastMeeting || null,
        face_image: face.face_image || face.person_image || null,
      };
    });
  };

  const updateFacePresence = (faces) => {
    const now = Date.now();
    const map = faceMapRef.current;
    faces.forEach((face, index) => {
      const id = face.id || `face-${index}`;
      const existing = map.get(id) || {};
      map.set(id, { ...existing, ...face, id, lastSeen: now });
    });

    for (const [id, face] of map.entries()) {
      if (now - face.lastSeen > ACTIVE_GRACE_MS) map.delete(id);
    }

    const list = Array.from(map.values());
    setDetectedFaces(list);
    setParticipants(list.filter(face => !face.unknown && face.name && face.name !== 'Unknown'));
  };

  const getFaceBoxStyle = (box) => {
    if (!box) return null;
    let x = box.x ?? box.left ?? box.x1 ?? (Array.isArray(box) ? box[0] : 0);
    let y = box.y ?? box.top ?? box.y1 ?? (Array.isArray(box) ? box[1] : 0);
    let w = box.w ?? box.width ?? box.w1 ?? (Array.isArray(box) ? box[2] : 0);
    let h = box.h ?? box.height ?? box.h1 ?? (Array.isArray(box) ? box[3] : 0);

    if (box.right != null && box.left != null) {
      x = box.left;
      w = box.right - box.left;
    }
    if (box.bottom != null && box.top != null) {
      y = box.top;
      h = box.bottom - box.top;
    }
    if (box.x2 != null && box.x1 != null) {
      x = box.x1;
      w = box.x2 - box.x1;
    }
    if (box.y2 != null && box.y1 != null) {
      y = box.y1;
      h = box.y2 - box.y1;
    }

    if (!w || !h) return null;

    const isNormalized = x <= 1 && y <= 1 && w <= 1 && h <= 1;
    const width = videoSize.width || 1;
    const height = videoSize.height || 1;

    const left = isNormalized ? x * 100 : (x / width) * 100;
    const top = isNormalized ? y * 100 : (y / height) * 100;
    const wPercent = isNormalized ? w * 100 : (w / width) * 100;
    const hPercent = isNormalized ? h * 100 : (h / height) * 100;

    return {
      left: `${Math.max(0, left)}%`,
      top: `${Math.max(0, top)}%`,
      width: `${Math.min(100, wPercent)}%`,
      height: `${Math.min(100, hPercent)}%`,
    };
  };

  const pollFaceRecognition = async () => {
    const status = pipelineStatusRef.current;
    if (status !== 'waiting') return;
    if (pendingMeetingRef.current) return;
    if (!videoRef.current || !canvasRef.current) return;
    if (isRecognizingRef.current) return;
    if (recognitionPausedRef.current) return;
    if (refreshingRef.current) return;

    const video = videoRef.current;
    if (video.videoWidth === 0 || video.videoHeight === 0) return;

    isRecognizingRef.current = true;

    try {
      const canvas = canvasRef.current;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const context = canvas.getContext('2d');
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      const frameBase64 = canvas.toDataURL('image/jpeg', 0.8);

      setCapturedImage(frameBase64);

      const recognizeResponse = await faceService.recognizeFaceBase64(frameBase64);
      if (recognizeResponse?.error) {
        setRecognitionError(recognizeResponse.error);
      } else if (recognitionErrorRef.current) {
        setRecognitionError(null);
      }

      const faces = normalizeFaces(recognizeResponse);
      if (faces.length > 0) {
        lastRecognitionAtRef.current = Date.now();
      }
      updateFacePresence(faces);
    } catch (err) {
      const recentlyRecognized = Date.now() - lastRecognitionAtRef.current < 2500;
      if (!recentlyRecognized) {
        const message = err?.error || err?.message || 'Face processing failed';
        setRecognitionError(message);
      }
      console.error('Face processing error:', err);
    } finally {
      isRecognizingRef.current = false;
    }
  };

  const setupAudioPipeline = async () => {
    if (mediaRecorderRef.current) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: true });
      audioStreamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }

      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const audioTracks = stream.getAudioTracks();
      const audioStream = new MediaStream(audioTracks);

      const analyser = audioContext.createAnalyser();
      const microphone = audioContext.createMediaStreamSource(stream);

      microphone.connect(analyser);
      analyser.fftSize = 512;
      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      try {
        const preferredMimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : (MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : '');

        mediaRecorderRef.current = preferredMimeType
          ? new MediaRecorder(audioStream, { mimeType: preferredMimeType })
          : new MediaRecorder(audioStream);
      } catch (e) {
        mediaRecorderRef.current = new MediaRecorder(audioStream);
      }

      mediaRecorderRef.current.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      mediaRecorderRef.current.onstop = processMeeting;

      const checkAudioLevel = () => {
        analyser.getByteFrequencyData(dataArray);
        const sum = dataArray.reduce((a, b) => a + b, 0);
        const average = sum / bufferLength;
        const speaking = average > 10;

        setVoiceActive(speaking);

        if (pipelineStatusRef.current === 'recording') {
          if (!speaking) {
            if (!silenceTimeoutRef.current) {
              silenceTimeoutRef.current = setTimeout(() => {
                stopSession();
              }, AUTO_STOP_SILENCE_MS);
            }
          } else if (silenceTimeoutRef.current) {
            clearTimeout(silenceTimeoutRef.current);
            silenceTimeoutRef.current = null;
          }
        }
        requestAnimationFrame(checkAudioLevel);
      };
      checkAudioLevel();
    } catch (err) {
      console.error('Mic access denied', err);
      setError('Microphone access is required for continuous monitoring.');
    }
  };

  const startSession = () => {
    const activeParticipants = participantsRef.current;
    if (!activeParticipants.length) return;
    setPipelineStatus('recording');
    setLockedParticipants(activeParticipants);
    audioChunksRef.current = [];
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'inactive') {
      mediaRecorderRef.current.start(1000);
    }
  };

  const stopSession = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      setPipelineStatus('processing');
    }
  };

  const processMeeting = async () => {
    try {
      setPipelineStatus('processing');
      const recordedMimeType = mediaRecorderRef.current?.mimeType || 'audio/webm';
      const audioBlob = new Blob(audioChunksRef.current, { type: recordedMimeType });
      const activeParticipants = lockedParticipantsRef.current;

      if (!activeParticipants.length) {
        setPipelineStatus('waiting');
        audioChunksRef.current = [];
        return;
      }

      if (audioBlob.size < MIN_AUDIO_BYTES) {
        setPipelineStatus('waiting');
        audioChunksRef.current = [];
        setLockedParticipants([]);
        return;
      }

      const processResponse = await audioService.processAudioFile(audioBlob);
      if (!processResponse.success) throw new Error(processResponse.error || 'Audio process failed');
      if (!processResponse.job_id) throw new Error('Audio processing job missing');

      const jobResult = await waitForAudioJob(processResponse.job_id);

      const participantIds = activeParticipants.map(p => p.person_id).filter(Boolean);
      const participantNames = activeParticipants.map(p => p.name).filter(Boolean);
      const participantGroupKey = buildParticipantKey(activeParticipants);

      const meetingPayload = {
        person_id: activeParticipants[0]?.person_id || null,
        person_name: activeParticipants[0]?.name || 'Unknown',
        participant_ids: participantIds,
        participant_names: participantNames,
        participant_group_key: participantGroupKey,
        transcript: jobResult.transcript,
        summary: jobResult.summary,
        audio_path: jobResult.audio_path || processResponse.audio_path,
        image_path: capturedImage,
      };

      setReviewData({
        transcript: jobResult.transcript,
        summary: jobResult.summary,
        audio_path: jobResult.audio_path || processResponse.audio_path,
      });

      setPendingMeeting({
        payload: meetingPayload,
        participants: activeParticipants,
      });
      setLastSavedMeeting(null);
      setLockedParticipants([]);
      audioChunksRef.current = [];
      setPipelineStatus('waiting');
    } catch (err) {
      console.error('Meeting Processing Failed', err);
      setError(err.message || 'Failed to complete meeting');
      setPipelineStatus('waiting');
      audioChunksRef.current = [];
      setLockedParticipants([]);
    }
  };

  const handleSaveMeeting = async () => {
    if (!pendingMeeting || isSavingMeeting) return;
    try {
      setIsSavingMeeting(true);
      const payload = {
        ...pendingMeeting.payload,
        transcript: reviewData.transcript,
        summary: reviewData.summary,
      };
      const createResponse = await meetingService.createMeeting(payload);
      const savedMeeting = createResponse?.meeting || createResponse?.data || null;

      const storedMeeting = {
        _id: savedMeeting?._id || `local-${Date.now()}`,
        summary: payload.summary,
        transcript: payload.transcript,
        timestamp: savedMeeting?.timestamp || new Date().toISOString(),
        participant_ids: payload.participant_ids,
        participant_names: payload.participant_names,
        person_id: payload.person_id,
        person_name: payload.person_name,
      };

      setRelatedMeetings(prev => [storedMeeting, ...prev.filter(m => m?._id !== storedMeeting._id)]);
      setLastSavedMeeting(storedMeeting);
      setLastSavedAt(Date.now());
      setPendingMeeting(null);
      loadRelatedMeetings(pendingMeeting.participants);
      await handleRefreshDetection();
    } catch (err) {
      setError(err?.message || err?.error || 'Failed to save meeting');
    } finally {
      setIsSavingMeeting(false);
    }
  };

  const handleResumeScan = () => {
    setRecognitionPaused(false);
    faceMapRef.current = new Map();
    setDetectedFaces([]);
    setParticipants([]);
    setRecognitionError(null);
  };

  const handleRefreshDetection = async () => {
    if (refreshingDetection) return;
    try {
      setRefreshingDetection(true);
      faceMapRef.current = new Map();
      setDetectedFaces([]);
      setParticipants([]);
      setRecognitionError(null);
      setRegistrationInputs({});
      setRegisteringIds({});

      const response = await faceService.refreshDetection();
      if (response?.success) {
        setRefreshToast('Face detection refreshed');
      } else {
        setError(response?.error || 'Failed to refresh face detection');
      }
    } catch (err) {
      setError(err?.error || err?.message || 'Failed to refresh face detection');
    } finally {
      setRefreshingDetection(false);
    }
  };

  const loadRelatedMeetings = async (activeParticipants) => {
    const participantIds = activeParticipants.map(p => p.person_id).filter(Boolean);
    const participantNames = activeParticipants.map(p => p.name).filter(Boolean);
    if (!participantIds.length && !participantNames.length) {
      setRelatedMeetings([]);
      return;
    }

    try {
      const response = await meetingService.getRelatedMeetings({
        participant_ids: participantIds,
        participant_names: participantNames,
        limit: 25,
      });
      const meetings = unwrapMeetings(response);

      if (!meetings.length) {
        setRelatedMeetings([]);
        return;
      }

      const scored = meetings.map(meeting => ({
        ...meeting,
        _score: meeting._score ?? computeMeetingScore(meeting, participantIds, participantNames)
      }));

      scored.sort((a, b) => {
        if (b._score !== a._score) return b._score - a._score;
        return new Date(b.timestamp) - new Date(a.timestamp);
      });

      setRelatedMeetings(scored);
    } catch (err) {
      console.error('Failed to load related meetings', err);
    }
  };

  const toggleMeetingDetails = (meetingId) => {
    setExpandedMeetingId((prev) => (prev === meetingId ? null : meetingId));
  };

  const waitForAudioJob = async (jobId) => {
    const timeoutMs = 120000;
    const intervalMs = 1500;
    const start = Date.now();

    while (Date.now() - start < timeoutMs) {
      const status = await audioService.getJobStatus(jobId);
      if (status?.status === 'completed') {
        return status;
      }
      if (status?.status === 'failed') {
        throw new Error(status?.error || 'Audio processing failed');
      }
      await new Promise(resolve => setTimeout(resolve, intervalMs));
    }

    throw new Error('Audio processing timed out');
  };

  const handleInlineRegister = async (face) => {
    const faceId = String(face.id);
    const name = (registrationInputs[faceId] || '').trim();
    if (!name) return;

    try {
      setRegisteringIds(prev => ({ ...prev, [faceId]: true }));
      const imageToUse = face.face_image || face.person_image || capturedImage;
      const res = await faceService.registerPerson(name, imageToUse);
      if (res.success) {
        setRegistrationInputs(prev => {
          const next = { ...prev };
          delete next[faceId];
          return next;
        });
        setRecognitionError(null);
        faceMapRef.current.delete(faceId);
        setDetectedFaces(prev => prev.filter(item => String(item.id) !== faceId));
      } else {
        setError(res.error || 'Registration failed');
      }
    } catch (err) {
      setError(err?.error || err?.message || 'Registration failed');
    } finally {
      setRegisteringIds(prev => {
        const next = { ...prev };
        delete next[faceId];
        return next;
      });
    }
  };

  const isDetecting = pipelineStatus === 'waiting';
  const isRecording = pipelineStatus === 'recording';
  const isProcessing = pipelineStatus === 'processing';
  const isJustSaved = lastSavedAt && Date.now() - lastSavedAt < 6000;
  const unknownDetected = pendingRegistrations.length > 0;
  const canStartRecording = isDetecting && participants.length > 0 && !unknownDetected;
  const displayedMeetings = searchQuery.trim() ? searchResults : relatedMeetings;
  const activeList = isRecording ? lockedParticipants : participants;

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#f6f3ee] via-white to-[#f1e9dd]">
      <div className="relative max-w-6xl mx-auto px-6 py-10 space-y-8">
        <div className="absolute -top-16 -right-24 w-64 h-64 bg-teal-200/40 blur-3xl rounded-full"></div>
        <div className="absolute -bottom-20 -left-20 w-72 h-72 bg-amber-200/40 blur-3xl rounded-full"></div>

        <header className="relative space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.35em] text-slate-500">Offline meeting memory</p>
              <h1 className="text-3xl md:text-4xl font-semibold text-slate-900">Live Meeting Console</h1>
              <p className="mt-2 text-slate-600 max-w-2xl">
                Continuous face recognition, automatic registration, and relationship-based memory — all in one screen.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-2 bg-white/90 backdrop-blur border border-amber-100 rounded-full px-4 py-2 shadow-sm">
                <div className={`h-2.5 w-2.5 rounded-full ${isRecording ? 'bg-rose-500' : 'bg-teal-500'}`}></div>
                <span className="text-sm font-medium text-slate-700">
                  {isRecording ? 'Recording' : isProcessing ? 'Processing' : 'Detecting'}
                </span>
              </div>
              <div className="flex items-center gap-2 bg-white/90 backdrop-blur border border-amber-100 rounded-full px-4 py-2 shadow-sm">
                {voiceActive ? <Mic className="w-4 h-4 text-teal-600" /> : <MicOff className="w-4 h-4 text-slate-400" />}
                <span className="text-sm font-medium text-slate-700">Voice {voiceActive ? 'Active' : 'Idle'}</span>
              </div>
              {isJustSaved && (
                <div className="flex items-center gap-2 bg-teal-50 border border-teal-200 rounded-full px-4 py-2">
                  <CheckCircle className="w-4 h-4 text-teal-600" />
                  <span className="text-sm font-medium text-teal-700">Saved</span>
                </div>
              )}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${isDetecting ? 'bg-teal-100 border-teal-200 text-teal-700' : 'bg-white border-amber-100 text-slate-500'}`}>
              Detecting
            </span>
            <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${isRecording ? 'bg-rose-100 border-rose-200 text-rose-700' : 'bg-white border-amber-100 text-slate-500'}`}>
              Recording
            </span>
            <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${isProcessing ? 'bg-amber-100 border-amber-200 text-amber-800' : 'bg-white border-amber-100 text-slate-500'}`}>
              Processing
            </span>
            <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${isJustSaved ? 'bg-teal-100 border-teal-200 text-teal-700' : 'bg-white border-amber-100 text-slate-500'}`}>
              Saved
            </span>
          </div>
        </header>

        {refreshToast && (
          <div className="fixed top-6 right-6 z-50 bg-slate-900 text-white text-sm px-4 py-2 rounded-full shadow-lg">
            {refreshToast}
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
            <p className="text-red-800 flex-1">{error}</p>
            <button className="text-sm text-red-800" onClick={() => setError(null)}>Dismiss</button>
          </div>
        )}

        {recognitionError && !error && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5" />
            <p className="text-amber-900 flex-1">{recognitionError}</p>
          </div>
        )}

        <section className="relative grid grid-cols-1 lg:grid-cols-[1.3fr_0.7fr] gap-6">
          <div className="bg-white/90 border border-amber-100 rounded-2xl shadow-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Camera className="w-5 h-5 text-slate-700" />
                <h2 className="text-lg font-semibold text-slate-900">Live Recognition</h2>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">{DETECTION_INTERVAL_MS}ms scan</span>
                <button
                  onClick={handleRefreshDetection}
                  disabled={refreshingDetection}
                  className={`text-xs font-semibold rounded-full px-3 py-1 border transition ${refreshingDetection
                    ? 'border-amber-100 text-slate-400 bg-amber-50/60'
                    : 'border-amber-100 text-slate-600 bg-white hover:bg-amber-50/50'}`}
                >
                  <span className="flex items-center gap-1.5">
                    {refreshingDetection
                      ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      : <RefreshCw className="w-3.5 h-3.5" />}
                    Rescan
                  </span>
                </button>
                {recognitionPaused && (
                  <button
                    onClick={handleResumeScan}
                    className="text-xs font-semibold text-teal-700 bg-teal-50 border border-teal-200 rounded-full px-3 py-1 hover:bg-teal-100"
                  >
                    Resume Scan
                  </button>
                )}
              </div>
            </div>

            <div className="relative w-full aspect-video bg-slate-900 rounded-2xl overflow-hidden border border-amber-100">
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="object-cover w-full h-full"
                onLoadedMetadata={() => {
                  if (!videoRef.current) return;
                  setVideoSize({
                    width: videoRef.current.videoWidth || 1280,
                    height: videoRef.current.videoHeight || 720,
                  });
                }}
              ></video>
              <canvas ref={canvasRef} className="hidden"></canvas>

              {!audioStreamRef.current && (
                <div className="absolute inset-0 bg-slate-900/80 flex flex-col items-center justify-center text-slate-200">
                  <Camera className="w-8 h-8 mb-2" />
                  Waiting for camera...
                </div>
              )}

              {detectedFaces.map((face) => {
                const style = getFaceBoxStyle(face.box);
                if (!style) return null;
                return (
                  <div
                    key={face.id}
                    className={`absolute border-2 rounded-xl transition-all duration-300 ${face.unknown ? 'border-amber-400 shadow-[0_0_16px_rgba(251,191,36,0.5)]' : 'border-teal-400 shadow-[0_0_16px_rgba(45,212,191,0.5)]'}`}
                    style={style}
                  >
                    <div className="absolute -top-6 left-0 text-xs font-semibold bg-slate-900/80 text-white px-2 py-1 rounded">
                      {face.name}
                      {face.confidence != null && ` ${(face.confidence * 100).toFixed(0)}%`}
                    </div>
                  </div>
                );
              })}

              {isRecording && (
                <div className="absolute inset-0 border-4 border-red-500 rounded-2xl animate-pulse"></div>
              )}
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Live participants</span>
              {detectedFaces.length === 0 && (
                <span className="text-sm text-slate-500">Scanning for faces...</span>
              )}
              {detectedFaces.map(face => (
                <span
                  key={`${face.id}-chip`}
                  className={`px-3 py-1 rounded-full text-xs font-medium border ${face.unknown ? 'border-amber-200 bg-amber-50 text-amber-700' : 'border-teal-200 bg-teal-50 text-teal-700'}`}
                >
                  {face.name}
                </span>
              ))}
            </div>

            {pendingRegistrations.length > 0 && (
              <div className="mt-5 space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Register new faces</p>
                  <span className="text-xs text-slate-500">{pendingRegistrations.length} pending</span>
                </div>
                <div className="space-y-3">
                  {pendingRegistrations.map((face) => (
                    <InlineRegistrationCard
                      key={`register-${face.id}`}
                      face={{
                        ...face,
                        preview: face.face_image || face.person_image || capturedImage
                      }}
                      name={registrationInputs[String(face.id)] || ''}
                      onNameChange={(value) =>
                        setRegistrationInputs(prev => ({ ...prev, [String(face.id)]: value }))
                      }
                      onRegister={() => handleInlineRegister(face)}
                      isSaving={Boolean(registeringIds[String(face.id)])}
                    />
                  ))}
                </div>
              </div>
            )}

            {unknownDetected && (
              <div className="mt-4 flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-xl px-3 py-2 text-amber-800 text-sm">
                <AlertCircle className="w-4 h-4" />
                New face detected — add a name in the sidebar to register.
              </div>
            )}
            {recognitionPaused && !unknownDetected && (
              <div className="mt-4 flex items-center gap-2 bg-teal-50 border border-teal-200 rounded-xl px-3 py-2 text-teal-800 text-sm">
                <CheckCircle className="w-4 h-4" />
                Recognition paused after match. Use Resume Scan to detect again.
              </div>
            )}
          </div>

          <div className="bg-white/90 border border-amber-100 rounded-2xl shadow-xl p-5 flex flex-col gap-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Users className="w-5 h-5 text-slate-700" />
                <h2 className="text-lg font-semibold text-slate-900">Session Control</h2>
              </div>
              <span className="text-xs text-slate-500">Auto-lock on record</span>
            </div>

            <div className="flex items-center justify-between bg-amber-50/50 border border-amber-100 rounded-xl px-4 py-3">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Recording timer</p>
                <p className="text-2xl font-semibold text-slate-900">{formatTimer(recordingSeconds)}</p>
              </div>
              <div className={`h-12 w-12 rounded-full flex items-center justify-center ${isRecording ? 'bg-rose-100 text-rose-600' : 'bg-teal-100 text-teal-600'}`}>
                {isRecording ? <StopCircle className="w-6 h-6" /> : <Play className="w-6 h-6" />}
              </div>
            </div>

            <button
              onClick={isRecording ? stopSession : startSession}
              disabled={isProcessing || (!isRecording && !canStartRecording)}
              className={`w-full px-6 py-4 rounded-2xl font-semibold text-lg transition-all shadow-lg ${isRecording
                ? 'bg-red-600 hover:bg-red-700 text-white'
                : 'bg-slate-900 hover:bg-slate-800 text-white'} ${isProcessing || (!isRecording && !canStartRecording) ? 'opacity-60 cursor-not-allowed' : ''}`}
            >
              {isRecording ? 'Stop Recording' : 'Start Recording'}
            </button>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-slate-700">
                  {isRecording ? 'Participants locked' : 'Active participants'}
                </p>
                <div className="flex items-center gap-1 text-xs text-slate-500">
                  <Activity className="w-3.5 h-3.5" />
                  {activeList.length} active
                </div>
              </div>
              {activeList.length === 0 && (
                <p className="text-sm text-slate-500">No participants recognized yet.</p>
              )}
              <div className="flex flex-wrap gap-2">
                {activeList.map(person => (
                  <span
                    key={`active-${person.id}`}
                    className="px-3 py-1 rounded-full text-xs font-medium border border-amber-100 bg-amber-50/40 text-slate-700"
                  >
                    {person.name}
                  </span>
                ))}
              </div>
            </div>

            <div className="text-xs text-slate-500 leading-relaxed">
              Detection pauses during recording to preserve performance. Unknown faces appear for inline registration.
            </div>
          </div>
        </section>

        <section className="grid grid-cols-1 lg:grid-cols-[1.2fr_0.8fr] gap-6">
          <div className="bg-white/95 border border-amber-100 rounded-2xl shadow-xl p-5">
            <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">Previous Meeting Summaries</h2>
                <p className="text-sm text-slate-500">Auto-sorted by active participants</p>
              </div>
              <div className="flex items-center gap-2 bg-amber-50/60 border border-amber-100 rounded-full px-3 py-1">
                <Search className="w-4 h-4 text-slate-500" />
                <input
                  type="text"
                  placeholder="Search meetings"
                  className="bg-transparent text-sm outline-none text-slate-700 placeholder:text-slate-400"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>

            {searching && (
              <div className="flex items-center gap-2 text-sm text-slate-500 mb-3">
                <Loader2 className="w-4 h-4 animate-spin" /> Searching meetings...
              </div>
            )}

            {displayedMeetings.length === 0 ? (
              <div className="border border-dashed border-amber-200 rounded-xl p-6 text-center text-slate-500">
                <p className="text-sm">No meeting memories found yet.</p>
                <p className="text-xs mt-1">Recognize participants to see combined history.</p>
              </div>
            ) : (
              <div className="space-y-3 max-h-[420px] overflow-y-auto pr-2">
                {displayedMeetings.map((meeting) => {
                  const participantNames = getUniqueNames(meeting.participant_names);
                  const isExpanded = expandedMeetingId === meeting._id;
                  return (
                    <div
                      key={meeting._id}
                      className={`border rounded-xl p-4 transition ${isExpanded
                        ? 'border-teal-300 bg-teal-50/40'
                        : 'border-amber-100 hover:border-amber-200'}`}
                    >
                      <div className="flex items-center justify-between gap-3 mb-2">
                        <p className="text-sm font-semibold text-slate-800">
                          {participantNames.length
                            ? participantNames.join(' + ')
                            : meeting.person_name || 'Meeting'}
                        </p>
                        <div className="flex items-center gap-3">
                          <span className="text-xs text-slate-500">
                            {meeting.timestamp
                              ? formatDistanceToNow(new Date(meeting.timestamp), { addSuffix: true })
                              : 'just now'}
                          </span>
                          <button
                            type="button"
                            onClick={() => toggleMeetingDetails(meeting._id)}
                            className="text-xs font-semibold text-teal-700 bg-teal-50 border border-teal-200 rounded-full px-3 py-1 hover:bg-teal-100"
                          >
                            {isExpanded ? 'Hide details' : 'View details'}
                          </button>
                        </div>
                      </div>
                      <p className="text-sm text-slate-600 line-clamp-3">
                        {meeting.summary || 'No summary available'}
                      </p>
                      {isExpanded && (
                        <div className="mt-3 border-t border-teal-200/70 pt-3 space-y-3">
                          <div className="text-xs uppercase tracking-wide text-teal-700 font-semibold">Meeting details</div>
                          <div className="space-y-2">
                            <p className="text-xs text-slate-500">Participants</p>
                            <div className="flex flex-wrap gap-2">
                              {(participantNames.length ? participantNames : [meeting.person_name || 'Unknown']).map((name, index) => (
                                <span
                                  key={`${meeting._id}-detail-name-${index}`}
                                  className="px-2 py-1 text-[11px] font-medium rounded-full bg-white border border-amber-100 text-slate-600"
                                >
                                  {name}
                                </span>
                              ))}
                            </div>
                          </div>
                          <div className="space-y-2">
                            <p className="text-xs text-slate-500">Transcript</p>
                            {splitIntoPoints(meeting.transcript).length ? (
                              <ol className="list-decimal list-inside space-y-2 text-sm text-slate-600">
                                {splitIntoPoints(meeting.transcript).map((point, index) => (
                                  <li key={`${meeting._id}-transcript-${index}`}>{point}</li>
                                ))}
                              </ol>
                            ) : (
                              <p className="text-sm text-slate-600">No transcript available.</p>
                            )}
                          </div>
                        </div>
                      )}
                      {participantNames.length > 1 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {participantNames.map((name, index) => (
                            <span key={`${meeting._id}-${name}-${index}`} className="text-[10px] uppercase tracking-wide text-slate-500">
                              {name}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="bg-white/95 border border-amber-100 rounded-2xl shadow-xl p-5 flex flex-col gap-5">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Live Transcript Preview</h2>
              <p className="text-sm text-slate-500">Updates after recording finishes</p>
            </div>
            <div className="bg-amber-50/60 border border-amber-100 rounded-xl p-4 min-h-[180px] text-sm text-slate-700 overflow-y-auto">
              {isProcessing && (
                <div className="flex items-center gap-2 text-sm text-slate-500">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Transcribing and summarizing...
                </div>
              )}
              {!isProcessing && pendingMeeting && (
                <div className="space-y-3">
                  <p className="text-xs text-slate-500">Edit transcript before saving.</p>
                  <textarea
                    className="w-full min-h-[140px] rounded-lg border border-amber-100 bg-white px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-200"
                    value={reviewData.transcript}
                    onChange={(e) => setReviewData(prev => ({ ...prev, transcript: e.target.value }))}
                  />
                </div>
              )}
              {!isProcessing && !pendingMeeting && !reviewData.transcript && (
                <p>Transcript will appear here after processing.</p>
              )}
              {!isProcessing && !pendingMeeting && reviewData.transcript && (
                <p>{reviewData.transcript}</p>
              )}
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-700">Meeting Summary</h3>
                {pendingMeeting && (
                  <span className="text-xs text-teal-600 font-semibold">Ready to save</span>
                )}
              </div>
              <div className="bg-teal-50/70 border border-teal-200 rounded-xl p-4 text-sm text-teal-900 min-h-[140px] space-y-4">
                {isProcessing ? (
                  <div className="flex items-center gap-2 text-sm text-teal-700">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Generating summary...
                  </div>
                ) : summarySections.summary.length > 0 ? (
                  <ol className="list-decimal list-inside space-y-2">
                    {summarySections.summary.map((point, index) => (
                      <li key={`summary-point-${index}`}>{point}</li>
                    ))}
                  </ol>
                ) : (
                  <p>Summary will appear after processing.</p>
                )}
                <div className="border-t border-teal-200/70 pt-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-teal-700">Action Items</p>
                  {isProcessing ? (
                    <p className="mt-2 text-teal-800/80">Waiting for action items...</p>
                  ) : summarySections.actions.length > 0 ? (
                    <ul className="mt-2 space-y-2">
                      {summarySections.actions.map((item, index) => (
                        <li key={`action-item-${index}`}>• {item}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-2 text-teal-800/80">No action items captured.</p>
                  )}
                </div>
              </div>
              {pendingMeeting && (
                <button
                  onClick={handleSaveMeeting}
                  disabled={isSavingMeeting}
                  className={`w-full px-4 py-3 rounded-xl font-semibold text-sm transition ${isSavingMeeting
                    ? 'bg-slate-200 text-slate-500'
                    : 'bg-teal-600 text-white hover:bg-teal-700'}`}
                >
                  {isSavingMeeting ? 'Saving meeting...' : 'Save Meeting'}
                </button>
              )}
              {!pendingMeeting && lastSavedMeeting?.summary && (
                <p className="text-xs text-slate-500">Last saved summary is shown above.</p>
              )}
            </div>
          </div>
        </section>

      </div>
    </div>
  );
}

