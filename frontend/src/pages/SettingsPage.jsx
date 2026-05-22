import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Settings, Camera, Mic, Database, Key, Save } from 'lucide-react';

export default function SettingsPage() {
  const navigate = useNavigate();
  const [settings, setSettings] = useState({
    // Camera Settings
    cameraResolution: '640x480',
    cameraDevice: 'default',

    // Audio Settings
    audioDevice: 'default',
    sampleRate: '16000',
    defaultDuration: '30',

    // AI Settings
    whisperModel: 'base',
    groqModel: 'llama-3.3-70b-versatile',
    liveTranscription: true,

    // Face Recognition Settings
    recognitionThreshold: 0.85,
    autoCapture: true,

    // Database Settings
    mongodbUri: 'mongodb://localhost:27017',
    databaseName: 'meeting_assistant',
  });

  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    // In a real app, this would save to localStorage or backend
    localStorage.setItem('meetingAssistantSettings', JSON.stringify(settings));
    setSaved(true);
    setTimeout(() => {
      setSaved(false);
      navigate('/');
    }, 1500);
  };

  useEffect(() => {
    // Load settings from localStorage
    const savedSettings = localStorage.getItem('meetingAssistantSettings');
    if (savedSettings) {
      setSettings(JSON.parse(savedSettings));
    }
  }, []);

  const updateSetting = (key, value) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.35em] text-slate-500">Preferences</p>
        <h1 className="text-3xl font-semibold text-slate-900">Settings</h1>
        <p className="mt-1 text-slate-600">Configure your Meeting Assistant</p>
      </div>

      {saved && (
        <div className="bg-teal-50 border border-teal-200 rounded-xl p-4">
          <p className="text-teal-800">Settings saved successfully! Redirecting to Dashboard...</p>
        </div>
      )}

      {/* Camera Settings */}
      <div className="bg-white/90 rounded-2xl border border-amber-100 p-6 shadow-sm">
        <div className="flex items-center space-x-2 mb-4">
          <Camera className="w-5 h-5 text-slate-600" />
          <h2 className="text-xl font-semibold text-slate-900">Camera Settings</h2>
        </div>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Camera Device
            </label>
            <select
              value={settings.cameraDevice}
              onChange={(e) => updateSetting('cameraDevice', e.target.value)}
              className="block w-full px-3 py-2 border border-amber-100 rounded-xl bg-white/80 text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-200 focus:border-teal-300"
            >
              <option value="default">Default Camera</option>
              <option value="0">Camera 0</option>
              <option value="1">Camera 1</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Resolution
            </label>
            <select
              value={settings.cameraResolution}
              onChange={(e) => updateSetting('cameraResolution', e.target.value)}
              className="block w-full px-3 py-2 border border-amber-100 rounded-xl bg-white/80 text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-200 focus:border-teal-300"
            >
              <option value="320x240">320x240</option>
              <option value="640x480">640x480 (Recommended)</option>
              <option value="1280x720">1280x720 (HD)</option>
              <option value="1920x1080">1920x1080 (Full HD)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Audio Settings */}
      <div className="bg-white/90 rounded-2xl border border-amber-100 p-6 shadow-sm">
        <div className="flex items-center space-x-2 mb-4">
          <Mic className="w-5 h-5 text-slate-600" />
          <h2 className="text-xl font-semibold text-slate-900">Audio Settings</h2>
        </div>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Microphone
            </label>
            <select
              value={settings.audioDevice}
              onChange={(e) => updateSetting('audioDevice', e.target.value)}
              className="block w-full px-3 py-2 border border-amber-100 rounded-xl bg-white/80 text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-200 focus:border-teal-300"
            >
              <option value="default">Default Microphone</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Sample Rate
            </label>
            <select
              value={settings.sampleRate}
              onChange={(e) => updateSetting('sampleRate', e.target.value)}
              className="block w-full px-3 py-2 border border-amber-100 rounded-xl bg-white/80 text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-200 focus:border-teal-300"
            >
              <option value="16000">16000 Hz (Recommended)</option>
              <option value="22050">22050 Hz</option>
              <option value="44100">44100 Hz</option>
              <option value="48000">48000 Hz</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Default Recording Duration (seconds)
            </label>
            <input
              type="number"
              value={settings.defaultDuration}
              onChange={(e) => updateSetting('defaultDuration', e.target.value)}
              min="5"
              max="300"
              className="block w-full px-3 py-2 border border-amber-100 rounded-xl bg-white/80 text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-200 focus:border-teal-300"
            />
          </div>
        </div>
      </div>

      {/* AI Settings */}
      <div className="bg-white/90 rounded-2xl border border-amber-100 p-6 shadow-sm">
        <div className="flex items-center space-x-2 mb-4">
          <Settings className="w-5 h-5 text-slate-600" />
          <h2 className="text-xl font-semibold text-slate-900">AI Settings</h2>
        </div>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Whisper Model
            </label>
            <select
              value={settings.whisperModel}
              onChange={(e) => updateSetting('whisperModel', e.target.value)}
              className="block w-full px-3 py-2 border border-amber-100 rounded-xl bg-white/80 text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-200 focus:border-teal-300"
            >
              <option value="tiny">Tiny (Fastest, Less Accurate)</option>
              <option value="base">Base (Recommended)</option>
              <option value="small">Small (Better Quality)</option>
              <option value="medium">Medium (High Quality)</option>
              <option value="large">Large (Best Quality, Slowest)</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Groq Model
            </label>
            <select
              value={settings.groqModel}
              onChange={(e) => updateSetting('groqModel', e.target.value)}
              className="block w-full px-3 py-2 border border-amber-100 rounded-xl bg-white/80 text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-200 focus:border-teal-300"
            >
              <option value="llama-3.3-70b-versatile">Llama 3.3 70B (Recommended)</option>
              <option value="llama-3.1-70b-versatile">Llama 3.1 70B</option>
              <option value="mixtral-8x7b-32768">Mixtral 8x7B</option>
              <option value="gemma2-9b-it">Gemma 2 9B</option>
            </select>
          </div>
          <div className="flex items-center">
            <input
              type="checkbox"
              checked={settings.liveTranscription}
              onChange={(e) => updateSetting('liveTranscription', e.target.checked)}
              className="h-4 w-4 text-teal-600 focus:ring-teal-200 border-amber-200 rounded"
            />
            <label className="ml-2 block text-sm text-slate-700">
              Enable Live Transcription
            </label>
          </div>
        </div>
      </div>

      {/* Face Recognition Settings */}
      <div className="bg-white/90 rounded-2xl border border-amber-100 p-6 shadow-sm">
        <div className="flex items-center space-x-2 mb-4">
          <Camera className="w-5 h-5 text-slate-600" />
          <h2 className="text-xl font-semibold text-slate-900">Face Recognition Settings</h2>
        </div>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Recognition Threshold: {settings.recognitionThreshold}
            </label>
            <input
              type="range"
              min="0.5"
              max="0.95"
              step="0.05"
              value={settings.recognitionThreshold}
              onChange={(e) => updateSetting('recognitionThreshold', parseFloat(e.target.value))}
              className="block w-full accent-teal-600"
            />
            <p className="text-xs text-slate-500 mt-1">
              Higher = stricter matching (fewer false positives)
            </p>
          </div>
          <div className="flex items-center">
            <input
              type="checkbox"
              checked={settings.autoCapture}
              onChange={(e) => updateSetting('autoCapture', e.target.checked)}
              className="h-4 w-4 text-teal-600 focus:ring-teal-200 border-amber-200 rounded"
            />
            <label className="ml-2 block text-sm text-slate-700">
              Auto-capture faces
            </label>
          </div>
        </div>
      </div>

      {/* Database Settings */}
      <div className="bg-white/90 rounded-2xl border border-amber-100 p-6 shadow-sm">
        <div className="flex items-center space-x-2 mb-4">
          <Database className="w-5 h-5 text-slate-600" />
          <h2 className="text-xl font-semibold text-slate-900">Database Settings</h2>
        </div>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              MongoDB URI
            </label>
            <input
              type="text"
              value={settings.mongodbUri}
              onChange={(e) => updateSetting('mongodbUri', e.target.value)}
              className="block w-full px-3 py-2 border border-amber-100 rounded-xl bg-white/80 text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-200 focus:border-teal-300 font-mono text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Database Name
            </label>
            <input
              type="text"
              value={settings.databaseName}
              onChange={(e) => updateSetting('databaseName', e.target.value)}
              className="block w-full px-3 py-2 border border-amber-100 rounded-xl bg-white/80 text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-200 focus:border-teal-300"
            />
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end space-x-4">
        <button
          onClick={handleSave}
          className="bg-slate-900 hover:bg-slate-800 text-white px-6 py-3 rounded-full font-semibold transition-colors flex items-center space-x-2 shadow-lg shadow-slate-900/20"
        >
          <Save className="w-5 h-5" />
          <span>Save Settings</span>
        </button>
      </div>
    </div>
  );
}
