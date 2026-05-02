import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Camera, Mic, User, CheckCircle, AlertCircle, Loader2, Square } from 'lucide-react';
import LoadingSpinner from '../components/Common/LoadingSpinner';
import faceService from '../services/faceService';
import meetingService from '../services/meetingService';
import audioService from '../services/audioService';

export default function StartMeetingPage() {
  const navigate = useNavigate();
  const [stage, setStage] = useState('capture'); // capture, register, recording, processing, complete
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Recognition data
  const [capturedImage, setCapturedImage] = useState(null);
  const [recognitionResult, setRecognitionResult] = useState(null);
  const [newPersonName, setNewPersonName] = useState('');

  // Recording data
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const audioChunksRef = useRef([]);

  const [meetingResult, setMeetingResult] = useState(null);

  // Step 1: Capture and recognize face
  const handleCaptureFace = async () => {
    try {
      setLoading(true);
      setError(null);

      // Capture face from camera
      const captureResponse = await faceService.captureface();
      setCapturedImage(captureResponse.image);

      // Recognize person
      const recognizeResponse = await faceService.recognizeFace(captureResponse.path);

      if (recognizeResponse.success) {
        setRecognitionResult(recognizeResponse);

        if (recognizeResponse.is_new || recognizeResponse.requires_registration) {
          // New person - need registration
          setStage('register');
        } else {
          // Recognized - go to recording
          setStage('recording');
        }
      } else {
        setError(recognizeResponse.error || 'Failed to recognize face');
      }
    } catch (err) {
      setError(err.error || 'Failed to capture face');
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Register new person
  const handleRegisterPerson = async () => {
    if (!newPersonName.trim()) {
      setError('Please enter a name');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await faceService.registerPerson(
        newPersonName.trim(),
        recognitionResult?.image_path || capturedImage
      );

      if (response.success) {
        setRecognitionResult({
          ...response,
          name: response.name,
          person_id: response.person_id,
          is_new: true,
          person_image: capturedImage
        });
        setStage('recording');
      } else {
        setError(response.error || 'Failed to register person');
      }
    } catch (err) {
      setError(err.error || 'Failed to register person');
    } finally {
      setLoading(false);
    }
  };

  // Step 3: Start unlimited meeting recording via browser Mic
  const handleStartRecording = async () => {
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      
      audioChunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        setIsRecording(false);
        setStage('processing');
        setLoading(true);

        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        
        // Stop all tracks to release mic hardware
        stream.getTracks().forEach(track => track.stop());

        try {
          // Process audio file
          const processResponse = await audioService.processAudioFile(audioBlob);
          
          if (!processResponse.success) {
            throw new Error(processResponse.error || 'Failed to process audio');
          }

          // Create meeting
          const meetingResponse = await meetingService.createMeeting({
            person_id: recognitionResult.person_id,
            person_name: recognitionResult.name,
            transcript: processResponse.transcript,
            summary: processResponse.summary,
            audio_path: processResponse.audio_path,
            image_path: capturedImage
          });

          if (meetingResponse.success) {
            setMeetingResult({
              ...meetingResponse.meeting,
              meeting_id: meetingResponse.meeting_id || meetingResponse.meeting?._id,
              summary: processResponse.summary, 
              transcript: processResponse.transcript
            });
            setStage('complete');
          } else {
            throw new Error(meetingResponse.error || 'Failed to create meeting');
          }
        } catch (err) {
          setError(err.message || 'Failed to complete meeting processing');
          setStage('recording');
        } finally {
          setLoading(false);
        }
      };

      recorder.start();
      setIsRecording(true);
      setMediaRecorder(recorder);
    } catch (err) {
      setError('Could not access microphone. Please ensure microphone permissions are granted.');
    }
  };

  const handleStopRecording = () => {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Start New Meeting</h1>
        <p className="mt-1 text-gray-600">Recognize a person and record a meeting</p>
      </div>

      {/* Progress Steps */}
      <div className="mb-8 flex items-center justify-center space-x-4">
        <div className={`flex items-center ${stage === 'capture' ? 'text-blue-600' : stage === 'register' || stage === 'recording' || stage === 'processing' || stage === 'complete' ? 'text-green-600' : 'text-gray-400'}`}>
          <Camera className="w-6 h-6" />
          <span className="ml-2 font-medium">Capture</span>
        </div>
        <div className="w-16 h-0.5 bg-gray-300"></div>
        <div className={`flex items-center ${stage === 'register' ? 'text-blue-600' : stage === 'recording' || stage === 'processing' || stage === 'complete' ? 'text-green-600' : 'text-gray-400'}`}>
          <User className="w-6 h-6" />
          <span className="ml-2 font-medium">Identify</span>
        </div>
        <div className="w-16 h-0.5 bg-gray-300"></div>
        <div className={`flex items-center ${stage === 'recording' || stage === 'processing' ? 'text-blue-600' : stage === 'complete' ? 'text-green-600' : 'text-gray-400'}`}>
          <Mic className="w-6 h-6" />
          <span className="ml-2 font-medium">Record</span>
        </div>
        <div className="w-16 h-0.5 bg-gray-300"></div>
        <div className={`flex items-center ${stage === 'complete' ? 'text-green-600' : 'text-gray-400'}`}>
          <CheckCircle className="w-6 h-6" />
          <span className="ml-2 font-medium">Complete</span>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 flex items-start">
          <AlertCircle className="w-5 h-5 text-red-600 mr-3 mt-0.5" />
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Stage: Capture Face */}
      {stage === 'capture' && (
        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="text-center">
            <Camera className="w-16 h-16 text-blue-600 mx-auto mb-4" />
            <h2 className="text-2xl font-semibold text-gray-900 mb-2">Capture Face</h2>
            <p className="text-gray-600 mb-8">
              Click the button below to capture a face from your camera
            </p>

            {capturedImage && (
              <div className="mb-6">
                <img src={capturedImage} alt="Captured" className="mx-auto rounded-lg shadow-md max-w-md" />
              </div>
            )}

            <button
              onClick={handleCaptureFace}
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-lg font-medium transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center space-x-2 mx-auto"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Capturing...</span>
                </>
              ) : (
                <>
                  <Camera className="w-5 h-5" />
                  <span>Capture Face</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Stage: Register New Person */}
      {stage === 'register' && (
        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="text-center mb-6">
            <User className="w-16 h-16 text-blue-600 mx-auto mb-4" />
            <h2 className="text-2xl font-semibold text-gray-900 mb-2">New Person Detected</h2>
            <p className="text-gray-600">Please provide the person's name</p>
          </div>

          {capturedImage && (
            <div className="mb-6">
              <img src={capturedImage} alt="Captured" className="mx-auto rounded-lg shadow-md max-w-xs" />
            </div>
          )}

          <div className="max-w-md mx-auto">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Full Name
            </label>
            <input
              type="text"
              value={newPersonName}
              onChange={(e) => setNewPersonName(e.target.value)}
              className="block w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Enter person's name"
              disabled={loading}
            />

            <div className="mt-6 flex space-x-4">
              <button
                onClick={() => setStage('capture')}
                disabled={loading}
                className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-800 px-6 py-3 rounded-lg font-medium transition-colors disabled:bg-gray-100 disabled:cursor-not-allowed"
              >
                Back
              </button>
              <button
                onClick={handleRegisterPerson}
                disabled={loading || !newPersonName.trim()}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Registering...</span>
                  </>
                ) : (
                  <span>Register & Continue</span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Stage: Recording */}
      {stage === 'recording' && recognitionResult && (
        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="text-center mb-8">
            <div className="mx-auto mb-4 relative w-48 h-48">
              {recognitionResult.person_image ? (
                <img 
                  src={recognitionResult.person_image} 
                  alt={recognitionResult.name} 
                  className="w-full h-full object-cover rounded-full border-4 border-green-500 shadow-md"
                />
              ) : (
                <CheckCircle className="w-16 h-16 text-green-600 mx-auto mt-8" />
              )}
              {!recognitionResult.is_new && recognitionResult.confidence && (
                <div className="absolute -bottom-2 -right-2 bg-green-100 text-green-800 text-xs font-bold px-2 py-1 rounded-full border border-green-200">
                  {(recognitionResult.confidence * 100).toFixed(1)}% Match
                </div>
              )}
            </div>
            
            <h2 className="text-2xl font-semibold text-gray-900 mb-2">
              {recognitionResult.is_new ? 'Person Registered!' : 'Person Recognized!'}
            </h2>
            <p className="text-xl text-gray-700">{recognitionResult.name}</p>
          </div>

          {recognitionResult.last_meeting && (
            <div className="mb-8 p-4 bg-blue-50 rounded-lg">
              <h3 className="font-semibold text-gray-900 mb-2">Last Meeting Summary:</h3>
              <div className="text-sm text-gray-700 whitespace-pre-line">{recognitionResult.last_meeting.summary}</div>
            </div>
          )}

          <div className="max-w-md mx-auto text-center">
            {isRecording ? (
              <div className="mb-6 flex flex-col items-center">
                <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center animate-pulse mb-4">
                  <Mic className="w-8 h-8 text-red-600" />
                </div>
                <p className="text-red-600 font-medium tracking-wide">Recording in progress...</p>
                <p className="text-gray-500 text-sm mt-1">Speak into your microphone</p>
              </div>
            ) : (
              <p className="text-gray-600 mb-6">
                Click below to start an unlimited recording. Press stop when the meeting is over.
              </p>
            )}

            <div className="mt-2 flex space-x-4">
              <button
                onClick={() => setStage('capture')}
                disabled={loading || isRecording}
                className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-800 px-6 py-3 rounded-lg font-medium transition-colors disabled:bg-gray-100 disabled:cursor-not-allowed"
              >
                Recapture Face
              </button>

              {isRecording ? (
                <button
                  onClick={handleStopRecording}
                  disabled={loading}
                  className="flex-1 bg-red-600 hover:bg-red-700 text-white px-6 py-3 rounded-lg font-medium transition-colors flex items-center justify-center space-x-2"
                >
                  <Square className="w-5 h-5 fill-current" />
                  <span>Stop Recording</span>
                </button>
              ) : (
                <button
                  onClick={handleStartRecording}
                  disabled={loading}
                  className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium transition-colors flex items-center justify-center space-x-2"
                >
                  <Mic className="w-5 h-5" />
                  <span>Start Recording</span>
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Stage: Processing */}
      {stage === 'processing' && (
        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="text-center">
            <LoadingSpinner size="xl" />
            <h2 className="text-2xl font-semibold text-gray-900 mt-6 mb-2">Processing Meeting</h2>
            <p className="text-gray-600 mb-4">
              Recording audio, transcribing, and generating summary...
            </p>
            <div className="max-w-md mx-auto space-y-2 text-left">
              <div className="flex items-center space-x-3 text-sm text-gray-600">
                <CheckCircle className="w-5 h-5 text-green-600" />
                <span>Recording audio from microphone</span>
              </div>
              <div className="flex items-center space-x-3 text-sm text-gray-600">
                <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
                <span>Transcribing with Whisper AI</span>
              </div>
              <div className="flex items-center space-x-3 text-sm text-gray-400">
                <div className="w-5 h-5 rounded-full border-2 border-gray-300"></div>
                <span>Generating summary with Groq AI</span>
              </div>
              <div className="flex items-center space-x-3 text-sm text-gray-400">
                <div className="w-5 h-5 rounded-full border-2 border-gray-300"></div>
                <span>Saving to database</span>
              </div>
            </div>
            <p className="text-sm text-gray-500 mt-6">
              This may take 30-60 seconds depending on recording length
            </p>
          </div>
        </div>
      )}

      {/* Stage: Complete */}
      {stage === 'complete' && meetingResult && (
        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="text-center mb-8">
            <CheckCircle className="w-20 h-20 text-green-600 mx-auto mb-4" />
            <h2 className="text-3xl font-bold text-gray-900 mb-2">Meeting Completed!</h2>
            <p className="text-gray-600">Your meeting has been recorded and processed</p>
          </div>

          <div className="space-y-6">
            <div className="p-4 bg-gray-50 rounded-lg">
              <h3 className="font-semibold text-gray-900 mb-2">Summary:</h3>
              <div className="text-sm text-gray-700 whitespace-pre-line">
                {meetingResult.summary}
              </div>
            </div>

            <div className="p-4 bg-gray-50 rounded-lg">
              <h3 className="font-semibold text-gray-900 mb-2">Transcript:</h3>
              <p className="text-sm text-gray-700">
                {meetingResult.transcript.substring(0, 300)}
                {meetingResult.transcript.length > 300 && '...'}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => navigate(`/meeting/${meetingResult.meeting_id}`)}
                className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium transition-colors"
              >
                View Full Details
              </button>
              <button
                onClick={() => {
                  setStage('capture');
                  setCapturedImage(null);
                  setRecognitionResult(null);
                  setMeetingResult(null);
                  setError(null);
                }}
                className="bg-gray-200 hover:bg-gray-300 text-gray-800 px-6 py-3 rounded-lg font-medium transition-colors"
              >
                Start Another Meeting
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
