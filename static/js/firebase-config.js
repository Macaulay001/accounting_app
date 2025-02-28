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

// Google Sign-In Function
async function googleSignIn() {
    try {
        const result = await signInWithPopup(auth, provider);
        const idToken = await result.user.getIdToken();
        const response = await fetch("/auth", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ idToken }),
        });
        return await response.json();
    } catch (error) {
        console.error("Error during sign-in:", error);
        throw error;
    }
}

export { googleSignIn };
