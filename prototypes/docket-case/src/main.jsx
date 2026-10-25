import React from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import DocketCase from './DocketCase.jsx';

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <main className="page">
      <DocketCase />
    </main>
  </React.StrictMode>
);
