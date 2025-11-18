# Frontend Authentication Migration: Clerk → AWS Cognito

## Migration Summary

Successfully migrated the frontend authentication from Clerk to AWS Cognito to match the backend authentication system.

## Changes Made

### 1. Dependencies

**Installed:**
- `aws-amplify` - AWS Amplify SDK for Cognito integration
- `@aws-amplify/ui-react` - Amplify UI components

**Removed:**
- `@clerk/clerk-react` - Clerk authentication library

### 2. New Files Created

#### Authentication Context
- **`frontend/src/contexts/AuthContext.jsx`**
  - Comprehensive authentication context using AWS Amplify
  - Provides hooks for login, signup, logout, password reset
  - Automatic token refresh and session management
  - Exports `useAuth()` hook for components

#### Login Component
- **`frontend/src/components/Auth/LoginPage.jsx`**
  - Full-featured login/signup interface
  - Email confirmation flow
  - Password reset functionality
  - Material-UI styled components

### 3. Modified Files

#### Core Application
- **`frontend/src/App.jsx`**
  - Replaced `ClerkProvider` with `AuthProvider`
  - Added `/login` route
  - Restructured routes to work with new auth system

- **`frontend/src/services/api.js`**
  - Updated to fetch Cognito tokens from Amplify session
  - Automatic token refresh on API requests
  - Proper 401 redirect to login page

- **`frontend/src/components/ProtectedRoute.jsx`**
  - Removed Clerk dependencies
  - Uses `useAuth()` hook from AuthContext
  - Simplified authentication check

#### UI Components
- **`frontend/src/components/Layout.jsx`**
  - Updated to use `useAuth()` instead of Clerk's `useUser()`
  - Removed Clerk-specific admin check (TODO: implement with Cognito groups)

- **`frontend/src/components/AuthButton.jsx`**
  - Completely rewritten for Cognito
  - Uses `useAuth()` for authentication state
  - Handles login/logout navigation

- **`frontend/src/components/SimpleChatInterface.jsx`**
  - Updated to use Cognito user data
  - Uses `user.username` instead of Clerk user properties

- **`frontend/src/components/AgentModeInterface.jsx`**
  - Updated to use Cognito authentication
  - Same user data structure changes as SimpleChatInterface

- **`frontend/src/components/UserProfileManager.jsx`**
  - Updated to use `useAuth()` hook
  - Removed Clerk-specific user properties

- **`frontend/src/pages/HomePage.jsx`**
  - Updated authentication check to use Cognito

- **`frontend/src/components/EnterprisePulse.jsx`**
  - Removed unused Clerk import

### 4. Environment Configuration

#### Updated Files
- **`frontend/.env`**
  ```env
  # AWS Cognito Authentication
  VITE_AWS_COGNITO_USER_POOL_ID=us-east-1_eMtGDVbAm
  VITE_AWS_COGNITO_APP_CLIENT_ID=2gbijesagdbe5mio2ici60r8bl
  VITE_AWS_REGION=us-east-1
  ```

- **`frontend/.env.example`**
  - Updated template with Cognito configuration
  - Removed Clerk references

## Configuration

The Cognito configuration matches the backend settings:

| Setting | Value |
|---------|-------|
| User Pool ID | `us-east-1_eMtGDVbAm` |
| App Client ID | `2gbijesagdbe5mio2ici60r8bl` |
| AWS Region | `us-east-1` |

## Authentication Flow

### Login
1. User navigates to `/login`
2. Enters username and password
3. Cognito authenticates and returns JWT tokens
4. Tokens stored in localStorage and Amplify session
5. User redirected to `/chat`

### Token Management
- Tokens automatically attached to API requests via axios interceptor
- Tokens refresh automatically when expired
- On 401 response, user redirected to login page

### Logout
- Clears Amplify session
- Removes tokens from localStorage
- Redirects to login page

## User Data Structure

### Clerk (Old)
```javascript
user = {
  id: "user_xxx",
  primaryEmailAddress: { emailAddress: "user@example.com" },
  fullName: "John Doe",
  firstName: "John",
  imageUrl: "https://..."
}
```

### Cognito (New)
```javascript
user = {
  username: "johndoe",
  userId: "xxx-xxx-xxx",
  signInDetails: {...}
}
```

## Testing Steps

### 1. Create a Test User
```bash
aws cognito-idp admin-create-user \
  --user-pool-id us-east-1_eMtGDVbAm \
  --username testuser \
  --user-attributes Name=email,Value=test@example.com \
  --temporary-password TempPassword123! \
  --message-action SUPPRESS
```

### 2. Start the Application
```bash
# Terminal 1 - Backend
cd backend
source venv/bin/activate
uvicorn src.main:app --reload

# Terminal 2 - Frontend
cd frontend
npm start
```

### 3. Test Authentication
1. Navigate to `http://localhost:5174`
2. Should redirect to `/login`
3. Sign in with test credentials
4. Should redirect to `/chat`
5. Verify token is sent to backend (check browser DevTools > Network)

### 4. Test Protected Routes
- Try accessing `/chat`, `/process-mining`, etc.
- Should work when authenticated
- Should redirect to login when not authenticated

### 5. Test Logout
- Click user avatar in top-right
- Click "Sign Out"
- Should clear session and redirect to login

## Known Issues & TODOs

### Admin Check (Layout.jsx:51)
Currently disabled. Need to implement admin check using Cognito groups:

```javascript
// TODO: Implement admin check
// Option 1: Parse JWT token for groups
// Option 2: Call backend API to check user groups
const isAdmin = false; // Currently hardcoded
```

**Solution:** Parse the Cognito ID token to check if user is in "Admins" group:
```javascript
import { fetchAuthSession } from 'aws-amplify/auth';

const checkIsAdmin = async () => {
  const session = await fetchAuthSession();
  const groups = session.tokens?.idToken?.payload['cognito:groups'] || [];
  return groups.includes('Admins');
};
```

### Backup Files
The following files still have Clerk imports but are not actively used:
- `frontend/src/App-enhanced.jsx`
- `frontend/src/components/AgentModeInterface.backup.jsx`
- `frontend/src/components/TopNavBar.jsx`
- `frontend/src/components/ProjectsHub.jsx`

These can be updated or removed as needed.

## Rollback Plan

If you need to rollback to Clerk:

1. Restore original files from git:
   ```bash
   git checkout HEAD -- frontend/src/App.jsx
   git checkout HEAD -- frontend/src/services/api.js
   git checkout HEAD -- frontend/src/components/ProtectedRoute.jsx
   # ... etc
   ```

2. Reinstall Clerk:
   ```bash
   npm install @clerk/clerk-react
   npm uninstall aws-amplify @aws-amplify/ui-react
   ```

3. Restore environment variables in `.env`

## Security Notes

- JWT tokens are stored in localStorage (standard practice for SPAs)
- Tokens automatically refresh before expiration
- API interceptor ensures fresh tokens on every request
- 401 responses automatically clear session and redirect to login
- HTTPS should be used in production

## Next Steps

1. **Create Cognito users** for your team
2. **Test all authentication flows** (login, signup, password reset)
3. **Implement admin check** using Cognito groups
4. **Update user profile functionality** to work with Cognito attributes
5. **Set up Cognito groups** in AWS Console (e.g., "Admins", "Users")
6. **Configure password policies** in Cognito User Pool settings
7. **Enable MFA** (optional) for enhanced security

## Support

For issues:
- Check browser console for errors
- Verify Cognito configuration in `.env`
- Ensure backend is running and configured for Cognito
- Check AWS Cognito User Pool settings

## Documentation

- [AWS Amplify Auth Docs](https://docs.amplify.aws/react/build-a-backend/auth/)
- [AWS Cognito Docs](https://docs.aws.amazon.com/cognito/)
- [Migration completed on: 2025-01-18]
