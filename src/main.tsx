import React from 'react';
import ReactDOM from 'react-dom/client';
import { MotionConfig } from 'motion/react';
import Landing from './Landing';
import './styles.css';
import './studio.css';
import './space.css';
import './light.css';
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><MotionConfig reducedMotion="user"><Landing /></MotionConfig></React.StrictMode>);
