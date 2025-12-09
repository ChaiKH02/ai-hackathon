import React, { useState } from 'react';
import './App.css';
import { Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './components/Layout/MainLayout';
import Dashboard from './components/Dashboard/Dashboard';
import Recommendations from './components/Recommendations/Recommendations';
import ActionsLog from './components/Actions_Log/actions_log';
import Feedback from './components/Feedback/Feedback';

function App() {
  console.log("API URL: ", process.env.REACT_APP_BACKEND_API_URL);
  return (
    <MainLayout>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/recommendations" element={<Recommendations />} />
        <Route path="/actions" element={<ActionsLog />} />
        <Route path="/feedbacks" element={<Feedback />} />
      </Routes>
    </MainLayout>
  );
}

export default App;
