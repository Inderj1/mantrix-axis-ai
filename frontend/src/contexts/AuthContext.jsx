import React, { createContext, useContext, useState, useEffect } from 'react';
import { Amplify } from 'aws-amplify';
import {
  signIn,
  signUp,
  signOut,
  confirmSignUp,
  resendSignUpCode,
  resetPassword,
  confirmResetPassword,
  getCurrentUser,
  fetchAuthSession,
} from 'aws-amplify/auth';

// Configure Amplify
const awsConfig = {
  Auth: {
    Cognito: {
      userPoolId: import.meta.env.VITE_AWS_COGNITO_USER_POOL_ID,
      userPoolClientId: import.meta.env.VITE_AWS_COGNITO_APP_CLIENT_ID,
      region: import.meta.env.VITE_AWS_REGION || 'us-east-1',
    },
  },
};

Amplify.configure(awsConfig);

const AuthContext = createContext({});

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(null);

  useEffect(() => {
    checkUser();
  }, []);

  const checkUser = async () => {
    try {
      const currentUser = await getCurrentUser();
      const session = await fetchAuthSession();

      setUser(currentUser);
      const idToken = session.tokens?.idToken?.toString();
      setToken(idToken);

      if (idToken) {
        localStorage.setItem('authToken', idToken);
      }
    } catch (error) {
      console.log('No authenticated user:', error);
      setUser(null);
      setToken(null);
      localStorage.removeItem('authToken');
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password) => {
    try {
      const { isSignedIn, nextStep } = await signIn({ username, password });

      if (isSignedIn) {
        await checkUser();
        return { success: true };
      }

      return { success: false, nextStep };
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  };

  const register = async (username, password, email, attributes = {}) => {
    try {
      const { isSignUpComplete, userId, nextStep } = await signUp({
        username,
        password,
        options: {
          userAttributes: {
            email,
            ...attributes,
          },
        },
      });

      return { success: true, isSignUpComplete, userId, nextStep };
    } catch (error) {
      console.error('Registration error:', error);
      throw error;
    }
  };

  const confirmRegistration = async (username, code) => {
    try {
      const { isSignUpComplete, nextStep } = await confirmSignUp({
        username,
        confirmationCode: code,
      });

      return { success: true, isSignUpComplete, nextStep };
    } catch (error) {
      console.error('Confirmation error:', error);
      throw error;
    }
  };

  const resendConfirmationCode = async (username) => {
    try {
      await resendSignUpCode({ username });
      return { success: true };
    } catch (error) {
      console.error('Resend code error:', error);
      throw error;
    }
  };

  const logout = async () => {
    try {
      await signOut();
      setUser(null);
      setToken(null);
      localStorage.removeItem('authToken');
    } catch (error) {
      console.error('Logout error:', error);
      throw error;
    }
  };

  const forgotPassword = async (username) => {
    try {
      const output = await resetPassword({ username });
      return { success: true, output };
    } catch (error) {
      console.error('Forgot password error:', error);
      throw error;
    }
  };

  const confirmForgotPassword = async (username, code, newPassword) => {
    try {
      await confirmResetPassword({
        username,
        confirmationCode: code,
        newPassword,
      });
      return { success: true };
    } catch (error) {
      console.error('Confirm forgot password error:', error);
      throw error;
    }
  };

  const refreshToken = async () => {
    try {
      const session = await fetchAuthSession({ forceRefresh: true });
      const idToken = session.tokens?.idToken?.toString();

      setToken(idToken);
      if (idToken) {
        localStorage.setItem('authToken', idToken);
      }

      return idToken;
    } catch (error) {
      console.error('Token refresh error:', error);
      throw error;
    }
  };

  const value = {
    user,
    token,
    loading,
    isAuthenticated: !!user,
    login,
    register,
    confirmRegistration,
    resendConfirmationCode,
    logout,
    forgotPassword,
    confirmForgotPassword,
    refreshToken,
    checkUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export default AuthContext;
