# Meeting Assistant - Full Stack Web Application

Complete web-based meeting assistant with face recognition, audio transcription, and AI-powered summarization.

## 🌟 Features

### Backend (Flask API)
- ✅ Face Recognition API (MTCNN + FaceNet)
- ✅ Audio Processing API (Whisper AI)
- ✅ Meeting Management API
- ✅ People Management API
- ✅ Statistics & Analytics API
- ✅ RESTful API with CORS support
- ✅ MongoDB integration

### Frontend (React + Vite)
- ✅ Modern React 18 with Hooks
- ✅ Redux Toolkit for state management
- ✅ React Router for navigation
- ✅ Tailwind CSS for styling
- ✅ Responsive design (mobile, tablet, desktop)
- ✅ Real-time updates
- ✅ Error handling & loading states

### Pages
1. **Dashboard** - Statistics and recent meetings
2. **Start Meeting** - Face recognition → Recording → Processing
3. **People Directory** - Browse all registered people
4. **Person Profile** - View individual profile and meeting history
5. **Meeting Details** - View transcript, summary, and metadata
6. **Settings** - Configure camera, audio, AI, and database settings

## 📁 Project Structure

```
miniproject/
├── backend/                    # Flask API Server
│   ├── app.py                 # Main Flask app
│   ├── routes/                # API route handlers
│   │   ├── face_routes.py     # Face recognition endpoints
│   │   ├── audio_routes.py    # Audio processing endpoints
│   │   ├── meeting_routes.py  # Meeting management endpoints
│   │   ├── people_routes.py   # People management endpoints
│   │   └── stats_routes.py    # Statistics endpoints
│   ├── requirements.txt       # Python dependencies
│   ├── start.sh              # Start script (Unix)
│   └── start.bat             # Start script (Windows)
│
├── frontend/                  # React Frontend
│   ├── src/
│   │   ├── components/       # React components
│   │   │   ├── Common/       # Shared components
│   │   │   └── Dashboard/    # Dashboard components
│   │   ├── pages/            # Page components
│   │   │   ├── HomePage.jsx
│   │   │   ├── StartMeetingPage.jsx
│   │   │   ├── PeoplePage.jsx
│   │   │   ├── PersonProfilePage.jsx
│   │   │   ├── MeetingDetailsPage.jsx
│   │   │   └── SettingsPage.jsx
│   │   ├── services/         # API service layer
│   │   │   ├── api.js
│   │   │   ├── faceService.js
│   │   │   ├── audioService.js
│   │   │   ├── meetingService.js
│   │   │   ├── peopleService.js
│   │   │   └── statsService.js
│   │   ├── store/            # Redux store
│   │   │   ├── store.js
│   │   │   ├── meetingSlice.js
│   │   │   ├── peopleSlice.js
│   │   │   └── uiSlice.js
│   │   ├── App.jsx           # Main app component
│   │   └── main.jsx          # Entry point
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── start.sh              # Start script (Unix)
│   └── start.bat             # Start script (Windows)
│
├── opencv/                    # Face recognition module (existing)
├── audio_to_text/            # Audio processing module (existing)
├── meeting_data/             # Storage for audio, images, transcripts
├── start-all.sh              # Start both frontend & backend (Unix)
└── start-all.bat             # Start both frontend & backend (Windows)
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+ with virtual environment
- Node.js 18+ and npm
- MongoDB (local or Atlas)
- Groq API key (free at https://console.groq.com/keys)
- Camera and microphone

### Setup

1. **Install Python Dependencies**
```bash
# Activate virtual environment
source .venv/Scripts/activate  # Windows
# or
source .venv/bin/activate       # Unix

# Install backend dependencies
cd backend
pip install -r requirements.txt
cd ..
```

2. **Install Frontend Dependencies**
```bash
cd frontend
npm install
cd ..
```

3. **Configure Environment**
```bash
# Create .env file in project root
echo "GROQ_API_KEY=your_api_key_here" > .env
```

4. **Start MongoDB**
```bash
# Windows: Start MongoDB service
# Linux/Mac: sudo systemctl start mongod
```

### Running the Application

#### Option 1: Start Everything Together (Recommended)
```bash
# Windows
start-all.bat

# Unix/Linux/Mac
./start-all.sh
```

#### Option 2: Start Separately
```bash
# Terminal 1: Backend
cd backend
./start.bat   # Windows
./start.sh    # Unix

# Terminal 2: Frontend
cd frontend
./start.bat   # Windows
./start.sh    # Unix
```

### Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:5000
- **API Health Check**: http://localhost:5000/api/health

## 📚 API Documentation

### Face Recognition API
```
POST   /api/face/capture          - Capture face from camera
POST   /api/face/detect            - Detect face in image
POST   /api/face/recognize         - Recognize person
POST   /api/face/register          - Register new person
GET    /api/face/camera/status     - Check camera status
```

### Audio Processing API
```
POST   /api/audio/record                    - Record audio
POST   /api/audio/transcribe                - Transcribe audio
POST   /api/audio/summarize                 - Summarize text
POST   /api/audio/record-and-transcribe     - Record + transcribe
GET    /api/audio/devices                   - List audio devices
```

### Meeting Management API
```
POST   /api/meeting/start            - Start complete meeting
POST   /api/meeting/create           - Create meeting from data
GET    /api/meeting/:id              - Get meeting details
GET    /api/meeting/list             - List all meetings
GET    /api/meeting/person/:id       - Get person's meetings
DELETE /api/meeting/:id              - Delete meeting
GET    /api/meeting/search?q=query   - Search meetings
```

### People Management API
```
GET    /api/people/                  - Get all people
GET    /api/people/:id               - Get person details
GET    /api/people/:id/meetings      - Get person's meetings
PUT    /api/people/:id               - Update person
DELETE /api/people/:id               - Delete person
GET    /api/people/search?q=query    - Search people
GET    /api/people/count             - Count people
```

### Statistics API
```
GET    /api/stats/dashboard          - Dashboard statistics
GET    /api/stats/people             - People statistics
GET    /api/stats/meetings/timeline  - Meeting timeline
```

## 🎯 Usage Flow

1. **Start New Meeting**
   - Click "Start Meeting" button
   - Camera captures face
   - System recognizes person (or register if new)
   - Shows last meeting summary (if returning)
   - Record meeting audio
   - System transcribes and summarizes
   - Meeting saved to database

2. **View People**
   - Browse all registered people
   - Search by name
   - Click person to view profile
   - See meeting history

3. **View Meetings**
   - Dashboard shows recent meetings
   - Click meeting for full details
   - View transcript and summary
   - Delete if needed

## 🛠️ Technology Stack

### Backend
- **Framework**: Flask 3.0
- **Database**: MongoDB (PyMongo)
- **Face Recognition**: MTCNN + FaceNet (PyTorch)
- **Speech-to-Text**: OpenAI Whisper
- **Summarization**: Groq API (Llama 3.3)
- **Audio**: sounddevice, numpy
- **CORS**: Flask-CORS
- **WebSocket**: Flask-SocketIO

### Frontend
- **Framework**: React 18
- **Build Tool**: Vite 5
- **State Management**: Redux Toolkit
- **Routing**: React Router v6
- **HTTP Client**: Axios
- **Styling**: Tailwind CSS 3
- **Icons**: Lucide React
- **Date Handling**: date-fns
- **Charts**: Recharts

## 🔧 Configuration

Settings can be configured through the Settings page in the frontend:
- Camera resolution and device
- Microphone and sample rate
- AI model selection (Whisper, Groq)
- Face recognition threshold
- MongoDB connection

## 🐛 Troubleshooting

### Backend Issues
```bash
# Check if MongoDB is running
mongo --eval "db.adminCommand('ping')"

# Check Python dependencies
pip list | grep -E "Flask|pymongo|opencv|torch|whisper"

# Check logs
# Backend prints detailed logs in terminal
```

### Frontend Issues
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Check if backend is accessible
curl http://localhost:5000/api/health
```

### Camera/Microphone Issues
- Ensure browser has camera/microphone permissions
- Check if another application is using the devices
- Try different browsers (Chrome recommended)

## 📝 Development

### Backend Development
```bash
cd backend
# Flask auto-reloads on file changes (debug=True)
python app.py
```

### Frontend Development
```bash
cd frontend
# Vite HMR auto-reloads on file changes
npm run dev
```

### Building for Production
```bash
cd frontend
npm run build
# Output in frontend/dist/
```

## 🎉 Features Completed

✅ Complete backend REST API
✅ Face recognition integration
✅ Audio recording and transcription
✅ AI-powered summarization
✅ Full-featured React frontend
✅ Redux state management
✅ Responsive design
✅ Error handling
✅ Loading states
✅ Search functionality
✅ Dashboard with statistics
✅ Meeting management
✅ People directory
✅ Settings page
✅ Startup scripts

## 📄 License

This project is for educational and demonstration purposes.

## 🤝 Contributing

This is a miniproject demonstration. For questions or issues, please refer to the documentation.

---

**Built with ❤️ using Flask, React, OpenCV, Whisper AI, and Groq**
