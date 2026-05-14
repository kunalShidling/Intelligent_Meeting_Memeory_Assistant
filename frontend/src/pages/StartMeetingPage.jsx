import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Camera, Mic, User, CheckCircle, AlertCircle, Loader2, MicOff } from 'lucide-react';
import LoadingSpinner from '../components/Common/LoadingSpinner';
import faceService from '../services/faceService';
import meetingService from '../services/meetingService';
import audioService from '../services/audioService';

export default function StartMeetingPage() {
  const navigate = useNavigate();
  // Status: 'waiting', 'recording', 'processing', 'review'
  const [pipelineStatus, setPipelineStatus] = useState('waiting');
  const [error, setError] = useState(null);
  const [reviewData, setReviewData] = useState({ transcript: '', summary: '', audio_path: '' });
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  
  const [recognitionResult, setRecognitionResult] = useState(null);
  const [capturedImage, setCapturedImage] = useState(null);
  const [voiceActive, setVoiceActive] = useState(false);
  const [newPersonName, setNewPersonName] = useState('');

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

  const isPersonPresentRef = useRef(false);
  const activeMeetingPersonRef = useRef(null);
  const MIN_AUDIO_BYTES = 5120;
  const PERSON_GRACE_MS = 6000;

  // --- Refs that mirror state so callbacks always see the latest value ---
  // Without these, setInterval / requestAnimationFrame closures capture stale state.
  const pipelineStatusRef = useRef('waiting');
  const recognitionResultRef = useRef(null);

  // Keep mirrors in sync
  useEffect(() => { pipelineStatusRef.current = pipelineStatus; }, [pipelineStatus]);
  useEffect(() => { recognitionResultRef.current = recognitionResult; }, [recognitionResult]);

  // Mount-only effect – NEVER re-runs when pipelineStatus changes.
  // Previously this had [pipelineStatus] as dep, which caused React to run the
  // cleanup (stopping MediaRecorder) every time a session started → instant
  // 'session too short' loop.
  useEffect(() => {
    setupAudioPipeline();
    loopRef.current = setInterval(pollFaceRecognition, 500);

    return () => {
      // True unmount cleanup only
      if (loopRef.current) clearInterval(loopRef.current);
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      if (audioStreamRef.current) {
        audioStreamRef.current.getTracks().forEach(t => t.stop());
      }
      if (silenceTimeoutRef.current) clearTimeout(silenceTimeoutRef.current);
    };
  }, []); // <-- mount/unmount ONLY

  // Backend Face Recognition Loop (500ms)
  // Uses refs (pipelineStatusRef, recognitionResultRef) so the setInterval callback
  // always reads the current value, not a stale closure.
  const pollFaceRecognition = async () => {
    const status = pipelineStatusRef.current;
    const lastResult = recognitionResultRef.current;
    if (status === 'processing' || lastResult?.requires_registration) return;
    if (!videoRef.current || !canvasRef.current) return;
    if (isRecognizingRef.current) return;

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

      // Recognize
      const recognizeResponse = await faceService.recognizeFaceBase64(frameBase64);
      
      if (recognizeResponse && recognizeResponse.success) {
        lastRecognitionAtRef.current = Date.now();
        setRecognitionResult(recognizeResponse);
        isPersonPresentRef.current = true;
        
        // If we are waiting and recognize a new person, open the modal
        if (pipelineStatusRef.current === 'waiting' && recognizeResponse?.requires_registration && !showRegisterModal) {
            setShowRegisterModal(true);
        }
      } else if (recognizeResponse?.requires_registration) {
        setRecognitionResult(recognizeResponse);
        isPersonPresentRef.current = true;
        if (pipelineStatusRef.current === 'waiting' && !showRegisterModal) {
            setShowRegisterModal(true);
        }
      } else {
        isPersonPresentRef.current = false;

        // Avoid replacing a recent successful detection with stale/noisy responses.
        const recentlyRecognized = Date.now() - lastRecognitionAtRef.current < 2500;
        if (!recentlyRecognized) {
          setRecognitionResult(prev => {
            if (prev?.requires_registration) return prev;
            if (recognizeResponse?.error) {
              return {
                name: prev?.name || 'Unknown',
                error: recognizeResponse.error,
                camera_detected: recognizeResponse.camera_detected,
                person_detected: recognizeResponse.person_detected,
              };
            }
            return { name: 'Unknown' };
          });
        }
      }
    } catch (err) {
      isPersonPresentRef.current = false;
      const recentlyRecognized = Date.now() - lastRecognitionAtRef.current < 2500;
      if (!recentlyRecognized) {
        const message = err?.error || err?.message || 'Face processing failed';
        setRecognitionResult(prev => ({
          name: prev?.name || 'Unknown',
          error: message,
        }));
      }
      console.error('Face processing error:', err);
    } finally {
      isRecognizingRef.current = false;
    }
  };

  const setupAudioPipeline = async () => {
    // Don't setup twice if restarting
    if (mediaRecorderRef.current) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: true });
      audioStreamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      
      // Extract audio stream for recording
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const audioTracks = stream.getAudioTracks();
      const audioStream = new MediaStream(audioTracks);
      
      const analyser = audioContext.createAnalyser();
      const microphone = audioContext.createMediaStreamSource(stream);
      
      microphone.connect(analyser);
      analyser.fftSize = 512;
      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      // MediaRecorder for actual recording - use audio stream only
      try {
        const preferredMimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : (MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : '');

        mediaRecorderRef.current = preferredMimeType
          ? new MediaRecorder(audioStream, { mimeType: preferredMimeType })
          : new MediaRecorder(audioStream);
      } catch (e) {
        // Fallback for browsers that don't support webm
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
        const speaking = average > 10; // Threshold for VAD
        
        setVoiceActive(speaking);

        // Use pipelineStatusRef so this rAF callback always reads the live value
        if (pipelineStatusRef.current === 'recording') {
            const personRecentlySeen = (Date.now() - lastRecognitionAtRef.current) < PERSON_GRACE_MS;
            if (!speaking && !personRecentlySeen) {
                // Person gone AND silent for 12 seconds → end the meeting
                if (!silenceTimeoutRef.current) {
                    silenceTimeoutRef.current = setTimeout(() => {
                        stopSession();
                    }, 12000);
                }
            } else {
                if (silenceTimeoutRef.current) {
                    clearTimeout(silenceTimeoutRef.current);
                    silenceTimeoutRef.current = null;
                }
            }
        }
        requestAnimationFrame(checkAudioLevel);
      };
      checkAudioLevel();
    } catch(err) {
      console.error("Mic access denied", err);
      setError("Microphone access is required for continuous monitoring.");
    }
  };

  const startSession = (person) => {
    console.log(`Starting continuous session for ${person.name}`);
    setPipelineStatus('recording');
    activeMeetingPersonRef.current = person;
    audioChunksRef.current = [];
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'inactive') {
        mediaRecorderRef.current.start(1000);
    }
  };

  const stopSession = () => {
    console.log("Stopping continuous session");
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      // Status becomes processing in onstop
      setPipelineStatus('processing');
    }
  };

  const processMeeting = async () => {
    try {
      setPipelineStatus('processing');
      const recordedMimeType = mediaRecorderRef.current?.mimeType || 'audio/webm';
      const audioBlob = new Blob(audioChunksRef.current, { type: recordedMimeType });
      const person = activeMeetingPersonRef.current;
      if(!person) return;

      if (audioBlob.size < MIN_AUDIO_BYTES) {
        // No real audio captured — soft reset without showing an error banner.
        // This happens when the session ends before the person speaks.
        console.warn('Session too short — no usable speech captured, resetting pipeline.');
        setPipelineStatus('waiting');
        activeMeetingPersonRef.current = null;
        audioChunksRef.current = [];
        return;
      }
      
      const processResponse = await audioService.processAudioFile(audioBlob);
      if (!processResponse.success) throw new Error(processResponse.error || "Audio process failed");

      setReviewData({
         transcript: processResponse.transcript,
         summary: processResponse.summary,
         audio_path: processResponse.audio_path
      });
      setPipelineStatus('review');

      // Clear recognized person for a brief cooldown? 
      setRecognitionResult({ name: "Waiting for next person..." });

    } catch (err) {
      console.error('Meeting Processing Failed', err);
      setError(err.message || 'Failed to complete meeting');
      setPipelineStatus('waiting');
      activeMeetingPersonRef.current = null;
      audioChunksRef.current = [];
    }
  };

  const handleSaveMeeting = async () => {
      try {
          const person = activeMeetingPersonRef.current;
          if(!person) return;
          
          await meetingService.createMeeting({
             person_id: person.person_id,
             person_name: person.name,
             transcript: reviewData.transcript,
             summary: reviewData.summary,
             audio_path: reviewData.audio_path,
             image_path: capturedImage
          });
          
          setPipelineStatus('waiting');
          activeMeetingPersonRef.current = null;
          audioChunksRef.current = [];
      } catch (err) {
          setError(err.message || 'Failed to save meeting');
      }
  };

  const handleCancelReview = () => {
      setPipelineStatus('waiting');
      activeMeetingPersonRef.current = null;
      audioChunksRef.current = [];
  };

  const handleManualRegister = async () => {
      if(newPersonName.trim()) {
        try {
            setPipelineStatus('processing');
            const res = await faceService.registerPerson(newPersonName.trim(), capturedImage);
            if (res.success) {
                setNewPersonName('');
                setRecognitionResult(null); // Will rescan automatically
                setShowRegisterModal(false);
            } else {
                setError(res.error || "Registration failed");
            }
        } catch(err) {
            setError(err.error || "Registration failed");
        } finally {
            setPipelineStatus('waiting');
        }
      }
  };

  const forceStop = () => stopSession();

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="mb-4">
        <h1 className="text-3xl font-bold text-gray-900 border-b pb-2 flex items-center gap-3">
            <span className="relative flex h-4 w-4 mr-2">
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${pipelineStatus === 'recording' ? 'bg-red-400' : 'bg-green-400'}`}></span>
                <span className={`relative inline-flex rounded-full h-4 w-4 ${pipelineStatus === 'recording' ? 'bg-red-500' : 'bg-green-500'}`}></span>
            </span>
            Continuous Meeting Pipeline
        </h1>
        <p className="mt-2 text-gray-600">The system is actively listening for voices and monitoring for faces.</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start">
          <AlertCircle className="w-5 h-5 text-red-600 mr-3 mt-0.5" />
          <p className="text-red-800">{error}</p>
          <button className="ml-auto text-sm text-red-800" onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      {recognitionResult?.error && !error && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-start">
          <AlertCircle className="w-5 h-5 text-amber-600 mr-3 mt-0.5" />
          <p className="text-amber-900">{recognitionResult.error}</p>
        </div>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Left: Camera & Person Status */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold flex items-center gap-2">
                <Camera className={isPersonPresentRef.current ? "text-blue-500" : "text-gray-400"} />
                Camera Feed
            </h2>
            <span className="text-xs bg-gray-100 text-gray-800 px-2 py-1 rounded">500ms loop</span>
          </div>

          <div className="relative w-full aspect-video bg-gray-100 rounded overflow-hidden flex items-center justify-center border-2 border-dashed border-gray-300">
             <video 
                ref={videoRef} 
                autoPlay 
                playsInline 
                muted 
                className="object-cover w-full h-full"
             ></video>
             <canvas ref={canvasRef} className="hidden"></canvas>
             
             {!audioStreamRef.current && (
                <div className="absolute inset-0 bg-gray-100 bg-opacity-90 flex flex-col items-center justify-center text-gray-400">
                    <Camera className="w-8 h-8 mb-2" />
                    Waiting for camera...
                </div>
             )}

             {/* Highlight overlay for active detection */}
             {recognitionResult && (
                 <div className={`absolute bottom-2 left-2 right-2 ${recognitionResult.error ? 'bg-red-600' : 'bg-black bg-opacity-70'} text-white px-3 py-2 rounded text-center font-medium backdrop-blur-sm truncate`}>
                     {recognitionResult.error ? recognitionResult.error : recognitionResult.name}
                     {recognitionResult.confidence && ` (${(recognitionResult.confidence * 100).toFixed(0)}%)`}
                 </div>
             )}
             {/* Pulsing red border when recording */}
             {pipelineStatus === 'recording' && (
                <div className="absolute inset-0 border-4 border-red-500 rounded-lg animate-pulse"></div>
             )}
          </div>

          {/* Registration Prompt if needed is now a modal */}

          {recognitionResult?.person_image && (
            <div className="mt-4 p-3 border border-gray-200 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-600 mb-2">Detected person image</p>
              <img
                src={recognitionResult.person_image}
                alt={recognitionResult.name || 'Detected person'}
                className="w-24 h-24 object-cover rounded-lg border border-gray-200"
              />
            </div>
          )}

          {/* Previous Meeting Summary Popup/Card */}
          {recognitionResult?.last_meeting && pipelineStatus === 'waiting' && (
            <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg animate-in fade-in slide-in-from-top-4 duration-500">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-bold text-green-800 flex items-center gap-2">
                  <CheckCircle size={14}/> Previous Meeting with {recognitionResult.name}
                </h3>
                <span className="text-[10px] text-green-600 font-medium">
                  {new Date(recognitionResult.last_meeting.timestamp).toLocaleDateString()}
                </span>
              </div>
              <div className="text-xs text-green-700 line-clamp-3 italic">
                "{recognitionResult.last_meeting.summary}"
              </div>
            </div>
          )}
        </div>

        {/* Right: Audio & Meeting Status */}
        <div className="bg-white rounded-lg shadow-lg p-6 flex flex-col">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            {voiceActive ? <Mic className="text-green-500" /> : <MicOff className="text-gray-400" />}
            Audio & Session Status
          </h2>

          <div className="flex-1 flex flex-col items-center justify-center space-y-6">
            
            {/* Core Status indicator */}
            <div className="text-center">
                {pipelineStatus === 'waiting' && (
                    <div className="text-gray-500 flex flex-col items-center">
                        <CheckCircle size={48} className="mb-3 text-gray-300" />
                        <p className="text-lg font-medium text-gray-700">Waiting for participants</p>
                    </div>
                )}

                {pipelineStatus === 'recording' && (
                    <div className="text-red-600 flex flex-col items-center">
                        <div className="relative mb-4">
                            <Mic size={64} />
                            <div className="absolute inset-0 bg-red-500 rounded-full -z-10 animate-pulse opacity-70"></div>
                        </div>
                        <p className="text-2xl font-bold">Session in progress...</p>
                        <p className="text-md mt-2 text-gray-600">
                            Recording <strong>{activeMeetingPersonRef.current?.name}</strong>
                        </p>
                    </div>
                )}

                {pipelineStatus === 'processing' && (
                    <div className="text-blue-600 flex flex-col items-center">
                        <Loader2 size={48} className="mb-3 animate-spin" />
                        <p className="text-lg font-medium">Processing Meeting...</p>
                        <p className="text-sm text-gray-500">Transcribing and saving results.</p>
                    </div>
                )}
            </div>

            {/* Manual Start for Unknown Person */}
            {pipelineStatus === 'waiting' && recognitionResult?.name === 'Unknown' && !recognitionResult?.requires_registration && (
                <button 
                  onClick={() => startSession({ name: 'Unknown', person_id: null })}
                  className="mt-8 bg-green-600 hover:bg-green-700 text-white px-8 py-3 rounded-full font-bold text-lg transition shadow-lg hover:shadow-xl"
                >
                  Start Recording for Unknown
                </button>
            )}

            {/* Start Recording for Known Person */}
            {pipelineStatus === 'waiting' && recognitionResult && recognitionResult.name !== 'Unknown' && !recognitionResult.requires_registration && (
                <button 
                  onClick={() => startSession(recognitionResult)}
                  className="mt-8 bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-full font-bold text-lg transition shadow-lg hover:shadow-xl flex items-center gap-2"
                >
                  <Mic size={24} />
                  Start Recording for {recognitionResult.name}
                </button>
            )}

            {/* Manual Override control */}
            {pipelineStatus === 'recording' && (
                <button 
                  onClick={forceStop}
                  className="mt-8 bg-red-600 hover:bg-red-700 text-white px-10 py-4 rounded-full font-bold text-xl transition shadow-lg hover:shadow-xl"
                >
                  Stop Recording
                </button>
            )}

          </div>
        </div>

        {/* Full screen review modal */}
        {pipelineStatus === 'review' && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60 p-4">
                <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
                    <div className="p-6 border-b border-gray-200">
                        <h2 className="text-2xl font-bold text-gray-800">Review Meeting: {activeMeetingPersonRef.current?.name}</h2>
                        <p className="text-sm text-gray-500">Edit the generated transcript and summary before saving.</p>
                    </div>
                    <div className="p-6 flex-1 overflow-y-auto space-y-6">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">Summary</label>
                            <textarea
                                className="w-full h-40 p-3 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
                                value={reviewData.summary}
                                onChange={(e) => setReviewData({...reviewData, summary: e.target.value})}
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">Transcript</label>
                            <textarea
                                className="w-full h-64 p-3 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
                                value={reviewData.transcript}
                                onChange={(e) => setReviewData({...reviewData, transcript: e.target.value})}
                            />
                        </div>
                    </div>
                    <div className="p-6 border-t border-gray-200 flex justify-end gap-4 bg-gray-50">
                        <button 
                            onClick={handleCancelReview}
                            className="px-6 py-2 border border-gray-300 text-gray-700 rounded hover:bg-gray-100"
                        >
                            Cancel
                        </button>
                        <button 
                            onClick={handleSaveMeeting}
                            className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 font-medium"
                        >
                            Save Meeting
                        </button>
                    </div>
                </div>
            </div>
        )}

        {/* Full screen register modal */}
        {showRegisterModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60 p-4">
                <div className="bg-white rounded-lg shadow-xl w-full max-w-md overflow-hidden">
                    <div className="p-6 border-b border-gray-200">
                        <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2"><User size={24} className="text-blue-500"/> New Person Detected</h2>
                        <p className="text-sm text-gray-500 mt-1">Please enter a name to register this new person in the database.</p>
                    </div>
                    <div className="p-6 space-y-4">
                        {capturedImage && (
                            <div className="flex justify-center">
                                <img src={capturedImage} alt="Captured" className="w-32 h-32 object-cover rounded-full border-4 border-blue-100" />
                            </div>
                        )}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">Full Name</label>
                            <input 
                                type="text" 
                                placeholder="Enter Name..." 
                                className="w-full px-4 py-2 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
                                value={newPersonName}
                                onChange={(e) => setNewPersonName(e.target.value)}
                                autoFocus
                            />
                        </div>
                    </div>
                    <div className="p-6 border-t border-gray-200 flex justify-end gap-3 bg-gray-50">
                        <button 
                            onClick={() => {
                                setShowRegisterModal(false);
                                setRecognitionResult({ name: "Unknown" });
                            }}
                            className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded"
                        >
                            Skip
                        </button>
                        <button 
                            onClick={handleManualRegister}
                            disabled={!newPersonName.trim() || pipelineStatus === 'processing'}
                            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 font-medium"
                        >
                            {pipelineStatus === 'processing' ? 'Registering...' : 'Register Person'}
                        </button>
                    </div>
                </div>
            </div>
        )}

      </div>
    </div>
  );
}

