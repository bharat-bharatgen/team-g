# Getting Started with InsureCopilot Frontend

Quick start guide to run the frontend application.

## 🚀 Quick Start (3 Steps)

### Step 1: Install Dependencies

```bash
cd frontend
npm install
```

This will install all required packages (~500MB, takes 2-3 minutes).

### Step 2: Start Development Server

```bash
npm run dev
```

The app will start at: **http://localhost:5173**

### Step 3: Start Backend (Separate Terminal)

Make sure your backend is running:

```bash
cd ../backend
docker-compose up
```

Backend should be running at: **http://localhost:8000**

---

## 🎯 First Time Setup

### Test the Application

1. **Open Browser**: Navigate to `http://localhost:5173`

2. **Sign Up**: 
   - Click "Sign up"
   - Enter name: `Test User`
   - Phone: `9876543210` (must start with 6/7/8/9)
   - Password: `password123`

3. **Create First Case**:
   - Click "New Case"
   - Click "Create Case"
   - You'll be redirected to case details

4. **Upload Documents**:
   - Click on any document type card (MER, Pathology, Photo, ID Proof)
   - Drag & drop files or click to browse
   - Click "Upload" button
   - Files will upload directly to S3

---

## 📁 Project Overview

### What Was Built

✅ **70+ Files Created**
- 9 UI Components (Button, Card, Input, etc.)
- 5 Auth Components (Signup, Login, Protected Route)
- 8 Dashboard Components
- 7 Upload Components
- 6 Case Management Components
- 3 Layout Components
- 5 Service Files (API layer)
- 3 Zustand Stores (State management)
- 8 Type Definition Files

### File Structure

```
frontend/
├── src/
│   ├── components/       # 30+ React components
│   ├── pages/           # 5 page components
│   ├── services/        # API integration
│   ├── store/           # State management
│   ├── types/           # TypeScript types
│   ├── utils/           # Helper functions
│   └── lib/             # Utilities
├── public/              # Static files
├── .env                 # Environment config (created)
├── package.json         # Dependencies
└── README.md           # Full documentation
```

---

## 🎨 Features Implemented

### Authentication
- [x] Signup with phone validation (Indian format)
- [x] Login with JWT tokens
- [x] Protected routes
- [x] Auto-redirect logic
- [x] Logout functionality

### Dashboard
- [x] Case statistics cards
- [x] Case list with status badges
- [x] Empty state for new users
- [x] Refresh functionality
- [x] Search and filter (UI ready)

### Case Management
- [x] Create new cases
- [x] View case details
- [x] Document type cards
- [x] Status tracking

### Document Upload
- [x] Drag & drop interface
- [x] Multi-file selection
- [x] Direct S3 upload with pre-signed URLs
- [x] Upload progress tracking
- [x] File preview (images)
- [x] Download functionality
- [x] Delete documents

### UI/UX
- [x] Responsive design (mobile, tablet, desktop)
- [x] Loading states
- [x] Error handling
- [x] Toast notifications
- [x] Clean blue + white theme
- [x] Indian date format (DD/MM/YYYY)
- [x] Phone number formatting

---

## 🔧 Development Commands

```bash
# Install dependencies
npm install

# Start dev server (http://localhost:5173)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run linter
npm run lint
```

---

## 🌐 API Endpoints Used

The frontend connects to these backend endpoints:

### Auth
- `POST /api/v1/auth/signup`
- `POST /api/v1/auth/signin`

### Cases
- `POST /api/v1/cases/`
- `GET /api/v1/cases/`
- `GET /api/v1/cases/{id}`

### Documents
- `POST /api/v1/cases/{id}/documents/upload-url`
- `POST /api/v1/cases/{id}/documents/confirm-upload`
- `GET /api/v1/cases/{id}/documents`
- `DELETE /api/v1/cases/{id}/documents/{type}`

---

## 🎯 Test Credentials

For testing, use these credentials:

**Phone Format**: 10 digits starting with 6, 7, 8, or 9

Valid examples:
- `9876543210` ✅
- `8765432109` ✅
- `7890123456` ✅
- `6123456789` ✅

Invalid examples:
- `1234567890` ❌ (starts with 1)
- `987654321` ❌ (only 9 digits)

---

## 🐛 Common Issues & Fixes

### Issue: "Failed to load cases"
**Fix**: Make sure backend is running on port 8000

### Issue: "CORS error"
**Fix**: Backend must have CORS configured for `http://localhost:5173`

### Issue: "Upload failed"
**Fix**: Check AWS S3 credentials in backend `.env` file

### Issue: "Module not found"
**Fix**: Run `npm install` again

### Issue: "Port 5173 already in use"
**Fix**: Kill existing process or Vite will auto-assign new port

---

## 📱 Mobile Testing

To test on mobile device:

1. Find your local IP: `ipconfig` (Windows) or `ifconfig` (Mac/Linux)
2. Update `.env`: `VITE_API_BASE_URL=http://YOUR_IP:8000/api/v1`
3. Run: `npm run dev -- --host`
4. Access from phone: `http://YOUR_IP:5173`

---

## 🚀 Deploy to Vercel

1. Push code to GitHub:
```bash
git add .
git commit -m "Add frontend"
git push
```

2. Go to [vercel.com](https://vercel.com)
3. Import your repository
4. Configure:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Vite
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
5. Add environment variable:
   - `VITE_API_BASE_URL` = your backend URL
6. Deploy!

---

## 📚 Next Steps

### Customize Branding
1. Update logo in `src/components/layout/Navbar.tsx`
2. Change app name in `.env`: `VITE_APP_NAME=YourName`
3. Update colors in `tailwind.config.js`

### Add Features
- Email notifications
- Export to PDF
- Advanced search
- Analytics dashboard
- Multi-language support

### Improve Performance
- Add React Query for caching
- Implement virtual scrolling for large lists
- Add service worker for offline support

---

## 💡 Pro Tips

1. **Hot Reload**: Changes auto-refresh in dev mode
2. **TypeScript**: Use VS Code for best autocomplete
3. **Components**: Check `src/components/ui/` for reusable components
4. **State**: Use Zustand stores for global state
5. **API Calls**: All in `src/services/` folder

---

## 🆘 Need Help?

- Check `README.md` for detailed documentation
- Review backend API docs at `http://localhost:8000/docs`
- Check browser console for errors (F12)

---

## ✅ Checklist

Before deploying:
- [ ] Test all user flows (signup → login → create case → upload)
- [ ] Verify mobile responsiveness
- [ ] Check error handling
- [ ] Test with backend
- [ ] Update environment variables
- [ ] Review security (no exposed keys)

---

**You're all set! Start building amazing insurance underwriting experiences! 🎉**
