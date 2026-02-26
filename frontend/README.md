# InsureCopilot Frontend

Modern React + TypeScript frontend for the BharatGen Insurance Underwriting Copilot platform.

## Features

- 🔐 **Authentication** - Phone number-based signup/login with JWT
- 📁 **Case Management** - Create and manage insurance underwriting cases
- 📤 **Document Upload** - Direct S3 upload with pre-signed URLs
- 📊 **Dashboard** - Real-time case statistics and overview
- 🎨 **Modern UI** - Clean, responsive design with Tailwind CSS
- 📱 **Fully Responsive** - Mobile-first design approach
- 🇮🇳 **Indian Localization** - Phone format (10 digits), DD/MM/YYYY dates

## Tech Stack

- **Framework**: React 18
- **Language**: TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui inspired components
- **State Management**: Zustand
- **Forms**: React Hook Form + Zod validation
- **Routing**: React Router v6
- **HTTP Client**: Axios
- **File Upload**: react-dropzone
- **Icons**: Lucide React

## Project Structure

```
frontend/
├── src/
│   ├── components/      # Reusable UI components
│   │   ├── ui/         # Base UI components (Button, Card, etc.)
│   │   ├── auth/       # Authentication components
│   │   ├── dashboard/  # Dashboard components
│   │   ├── upload/     # File upload components
│   │   ├── cases/      # Case management components
│   │   └── layout/     # Layout components (Navbar, etc.)
│   ├── pages/          # Page components
│   ├── services/       # API service layer
│   ├── store/          # Zustand state stores
│   ├── types/          # TypeScript type definitions
│   ├── utils/          # Utility functions
│   ├── lib/            # Helper libraries
│   ├── App.tsx         # Main app component
│   └── main.tsx        # App entry point
├── public/             # Static assets
└── package.json
```

## Prerequisites

- Node.js 18+ and npm
- Backend API running (default: `http://localhost:8000`)

## Getting Started

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Environment Configuration

Create a `.env` file in the frontend directory:

```bash
cp .env.example .env
```

Update the `.env` file:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_APP_NAME=InsureCopilot
```

### 3. Run Development Server

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### 4. Build for Production

```bash
npm run build
```

The production build will be in the `dist/` folder.

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build locally
- `npm run lint` - Run ESLint

## Key Features

### Authentication

- **Signup**: Register with name, phone (10 digits), and password
- **Login**: Sign in with phone number and password
- **Protected Routes**: Automatic redirect to login if not authenticated
- **Token Management**: JWT tokens stored in localStorage

### Case Management

- **Create Case**: Initialize a new underwriting case
- **View Cases**: Dashboard with case statistics and list
- **Case Details**: View and manage individual case documents

### Document Upload

Supports 4 document types:
- 📋 **MER** (Medical Examination Report)
- 🧪 **Pathology** (Lab/Pathology Reports)
- 📷 **Photo** (Geo-tagged Photographs)
- 🪪 **ID Proof** (Identification Documents)

**Upload Flow**:
1. Select document type
2. Drag & drop or browse files (PDF, JPEG, PNG)
3. Files upload directly to AWS S3
4. Progress tracking for each file
5. Preview and download uploaded documents

### Dashboard

- Total cases count
- Pending cases
- Completed cases
- Failed cases
- Recent cases grid
- Quick actions (New Case, Refresh)

## API Integration

The frontend communicates with the backend API through the following endpoints:

### Auth
- `POST /auth/signup` - Register new user
- `POST /auth/signin` - Login

### Cases
- `POST /cases/` - Create new case
- `GET /cases/` - List all cases
- `GET /cases/{id}` - Get case details

### Documents
- `POST /cases/{id}/documents/upload-url` - Get pre-signed upload URLs
- `POST /cases/{id}/documents/confirm-upload` - Confirm upload completion
- `GET /cases/{id}/documents` - Get documents with download URLs
- `DELETE /cases/{id}/documents/{type}` - Delete documents by type

## Styling & Theming

### Color Palette

**Primary (Blue)**:
- Primary: `#2563eb` (Blue 600)
- Hover: `#1e40af` (Blue 700)
- Light: `#dbeafe` (Blue 50)

**Status Colors**:
- Created: Slate
- Processing: Blue
- Completed: Green
- Failed: Red

### Responsive Breakpoints

- Mobile: `0-640px`
- Tablet: `641-1024px`
- Desktop: `1025px+`

## Deployment

### Vercel (Recommended)

1. Push code to GitHub
2. Import project in Vercel
3. Configure:
   - **Framework**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Add environment variables in Vercel dashboard
5. Deploy!

### Other Platforms

Build the project and serve the `dist/` folder:

```bash
npm run build
# Serve dist/ with any static hosting service
```

## Development Tips

### Adding New Pages

1. Create page component in `src/pages/`
2. Add route in `src/App.tsx`
3. Update navigation as needed

### Adding New API Services

1. Create service file in `src/services/`
2. Define types in `src/types/`
3. Use axios instance from `src/services/api.ts`

### State Management

- Use Zustand stores for global state
- Create new stores in `src/store/`
- Keep stores focused and minimal

### Form Validation

- Use Zod schemas in `src/utils/validation.ts`
- Integrate with React Hook Form using `@hookform/resolvers/zod`

## Troubleshooting

### CORS Issues

Ensure backend has CORS configured for `http://localhost:5173`

### API Connection Failed

Check that:
- Backend is running on port 8000
- `VITE_API_BASE_URL` is correct in `.env`
- Network/firewall not blocking requests

### Upload Failing

- Check S3 credentials in backend
- Verify file types (PDF, JPEG, PNG only)
- Check browser console for errors

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## License

Proprietary - BharatGen Insurance Copilot

## Support

For issues or questions, contact the development team.
