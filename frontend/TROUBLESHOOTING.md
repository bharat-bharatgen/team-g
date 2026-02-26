# Troubleshooting Guide

## Issue Fixed: White Screen on Load

### What Was the Problem?
The initial white screen was caused by the `vite.config.ts` using Node's `path` module without proper configuration.

### What Was Fixed?
1. **vite.config.ts** - Changed from `path.resolve` to `fileURLToPath` (native ESM)
2. **Dashboard** - Added better error handling for API calls
3. **App.tsx** - Restored all routes with proper error boundaries

---

## Current Status ✅

Your app should now show:
- ✅ **Login Page** at `/login`
- ✅ **Signup Page** at `/signup`
- ✅ **Dashboard** at `/dashboard` (after login)
- ✅ All protected routes working

---

## Testing the App

### 1. Start Backend (Terminal 1)
```bash
cd backend
docker-compose up
```
Backend should be running at: `http://localhost:8000`

### 2. Start Frontend (Terminal 2)
```bash
cd frontend
npm run dev
```
Frontend should be running at: `http://localhost:5173`

### 3. Test Signup Flow
1. Go to `http://localhost:5173/signup`
2. Enter:
   - Name: `Test User`
   - Phone: `9876543210` (must start with 6/7/8/9)
   - Password: `password123`
3. Click "Sign Up"
4. You should be redirected to dashboard

### 4. Test Dashboard
- If backend is running: You'll see "No cases yet" empty state
- If backend is NOT running: You'll see an error message
- Click "New Case" to create your first case

---

## Common Issues & Solutions

### Issue: Dashboard shows error "Failed to load cases"
**Solution**: Make sure backend is running on port 8000
```bash
cd backend
docker-compose up
```

### Issue: CORS error in browser console
**Solution**: Backend needs CORS configured. Check backend `.env` and ensure it allows `http://localhost:5173`

### Issue: "Cannot find module '@/...'"
**Solution**: The path aliases are configured. If you still see this:
1. Stop dev server (Ctrl+C)
2. Delete `node_modules` and reinstall:
```bash
rm -rf node_modules
npm install
npm run dev
```

### Issue: Styles not loading (no colors)
**Solution**: 
1. Check if `index.css` is imported in `main.tsx`
2. Restart dev server
3. Clear browser cache (Ctrl+Shift+R)

---

## Browser Console Tips

Press **F12** to open browser console and check:
- **Console Tab**: JavaScript errors (red text)
- **Network Tab**: API calls (look for failed requests)
- **Elements Tab**: Inspect HTML/CSS

---

## Environment Variables

Make sure `.env` file exists in frontend folder:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_APP_NAME=InsureCopilot
```

If you change `.env`, restart the dev server.

---

## File Structure (If You Need to Debug)

```
frontend/src/
├── App.tsx              # Main routes
├── main.tsx            # React entry point
├── index.css           # Global styles
├── components/
│   ├── auth/           # Login, Signup, Protected routes
│   ├── dashboard/      # Dashboard components
│   ├── layout/         # Navbar, Layout
│   └── ui/             # Reusable UI components
├── pages/              # Page components
├── services/           # API calls
├── store/              # State management (Zustand)
└── utils/              # Helper functions
```

---

## Next Steps

1. **Test Login/Signup** - Make sure auth works
2. **Start Backend** - Required for dashboard to load data
3. **Create First Case** - Click "New Case" button
4. **Upload Documents** - Test the upload functionality

---

## Getting Help

If you still have issues:
1. Check browser console (F12) for errors
2. Check backend logs in terminal
3. Verify both servers are running
4. Check `GETTING_STARTED.md` for detailed setup

---

**Your app is now working! 🎉**
