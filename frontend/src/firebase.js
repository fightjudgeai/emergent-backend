import firebase from 'firebase/compat/app';
import 'firebase/compat/firestore';

const firebaseConfig = {
  apiKey: "AIzaSyDr5EZaw9eyrkB7OzvrhY9kIfcyMRqd8l4",
  authDomain: "fight-judge-a-i-pro-y2jutw.firebaseapp.com",
  projectId: "fight-judge-a-i-pro-y2jutw",
  storageBucket: "fight-judge-a-i-pro-y2jutw.firebasestorage.app",
  messagingSenderId: "438068888147",
  appId: "1:438068888147:web:9d9d40cc838710091ffca6"
};

const app = initializeApp(firebaseConfig);
export const db = getFirestore(app);