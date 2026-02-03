# Frontend JWT Authentication Guide

## API Endpoints for Authentication

### 1. Login
**POST** `/api/auth/login`

```json
{
  "username": "admin_username",
  "password": "password"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "username": "admin_username",
    "email": "admin@example.com",
    "role": "admin",
    "first_name": "John",
    "last_name": "Doe"
  },
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### 2. Get Current User
**GET** `/api/auth/me`
Headers: `Authorization: Bearer <access_token>`

### 3. Refresh Access Token
**POST** `/api/auth/refresh`
Headers: `Authorization: Bearer <refresh_token>`

### 4. Logout
**POST** `/api/auth/logout`
Headers: `Authorization: Bearer <access_token>`

## Frontend Implementation Example (JavaScript)

### Login Function
```javascript
async function login(username, password) {
  try {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, password }),
    });
    
    const data = await response.json();
    
    if (data.success) {
      // Store tokens securely
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      localStorage.setItem('user', JSON.stringify(data.data));
      return data.data;
    } else {
      throw new Error(data.error);
    }
  } catch (error) {
    console.error('Login failed:', error);
    throw error;
  }
}
```

### API Call with Authentication
```javascript
async function makeAuthenticatedRequest(url, options = {}) {
  const token = localStorage.getItem('access_token');
  
  const defaultOptions = {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  };
  
  try {
    const response = await fetch(url, {
      ...defaultOptions,
      ...options,
      headers: {
        ...defaultOptions.headers,
        ...options.headers,
      },
    });
    
    // Handle token expiration
    if (response.status === 401) {
      await refreshAccessToken();
      // Retry request with new token
      const newToken = localStorage.getItem('access_token');
      defaultOptions.headers['Authorization'] = `Bearer ${newToken}`;
      return fetch(url, { ...defaultOptions, ...options });
    }
    
    return response;
  } catch (error) {
    console.error('API request failed:', error);
    throw error;
  }
}
```

### Refresh Access Token
```javascript
async function refreshAccessToken() {
  const refreshToken = localStorage.getItem('refresh_token');
  
  try {
    const response = await fetch('/api/auth/refresh', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${refreshToken}`,
        'Content-Type': 'application/json',
      },
    });
    
    const data = await response.json();
    
    if (data.success) {
      localStorage.setItem('access_token', data.access_token);
      return data.access_token;
    } else {
      // Refresh token invalid, redirect to login
      logout();
      throw new Error('Session expired');
    }
  } catch (error) {
    logout();
    throw error;
  }
}
```

### Logout Function
```javascript
async function logout() {
  try {
    const token = localStorage.getItem('access_token');
    if (token) {
      await fetch('/api/auth/logout', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
    }
  } catch (error) {
    console.error('Logout error:', error);
  } finally {
    // Clear stored tokens and user data
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    // Redirect to login page
    window.location.href = '/login';
  }
}
```

## React Hook Example

```javascript
import { useState, useEffect } from 'react';

export function useAuth() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    const userData = localStorage.getItem('user');
    
    if (token && userData) {
      setUser(JSON.parse(userData));
    }
    setLoading(false);
  }, []);

  const login = async (username, password) => {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    
    const data = await response.json();
    if (data.success) {
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      localStorage.setItem('user', JSON.stringify(data.data));
      setUser(data.data);
    }
    return data;
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    setUser(null);
  };

  return { user, loading, login, logout };
}
```

## Bluehost Deployment Notes

1. **CORS Configuration**: The app includes CORS support for frontend domains
2. **Token Storage**: Use localStorage or httpOnly cookies for production
3. **HTTPS**: Ensure your Bluehost site uses HTTPS for secure token transmission
4. **Environment Variables**: Set JWT_SECRET_KEY in your Bluehost environment

## Security Considerations

1. **Token Expiration**: Access tokens expire in 1 hour, refresh tokens in 30 days
2. **HTTPS Required**: Always use HTTPS in production
3. **Secure Storage**: Consider httpOnly cookies for better security
4. **Token Validation**: Backend validates all JWT tokens automatically