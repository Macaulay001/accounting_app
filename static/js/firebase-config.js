import { initializeApp } from "https://www.gstatic.com/firebasejs/10.9.0/firebase-app.js";
import { getAuth, signInWithPopup, GoogleAuthProvider } from "https://www.gstatic.com/firebasejs/10.9.0/firebase-auth.js";

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
    apiKey: "AIzaSyBFZZhJDUzjiF2Hip_OkuRPsVQy9wcXWbY",
    authDomain: "ponmoapp.firebaseapp.com",
    projectId: "ponmoapp",
    storageBucket: "ponmoapp.firebasestorage.app",
    messagingSenderId: "591208192826",
    appId: "1:591208192826:web:0d5ae9ec5b4fcd371c0e03",
    measurementId: "G-SY8669ENZL"
  };

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const provider = new GoogleAuthProvider();

// Configure Firebase Auth for local development
if (window.location.hostname === '127.0.0.1') {
    auth.useDeviceLanguage();
    // Force HTTP for local development
    auth.settings.appVerificationDisabledForTesting = true;
}

// Google Sign-In Function
async function googleSignIn() {
    try {
        console.log('Starting Google Sign-In...');
        console.log('Current hostname:', window.location.hostname);
        console.log('Current origin:', window.location.origin);
        
        // Remove custom parameters - use default Firebase handling
        
        console.log('Calling signInWithPopup...');
        const result = await signInWithPopup(auth, provider);
        console.log('Sign-in successful:', result);
        
        const idToken = await result.user.getIdToken();
        console.log('Got ID token, sending to backend...');
        
        const response = await fetch("/auth", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ idToken }),
        });
        
        const responseData = await response.json();
        console.log('Backend response:', responseData);
        return responseData;
    } catch (error) {
        console.error("Detailed error during sign-in:", error);
        console.error("Error code:", error.code);
        console.error("Error message:", error.message);
        throw error;
    }
}

export { googleSignIn };
