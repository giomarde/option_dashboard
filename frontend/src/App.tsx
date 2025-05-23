// src/App.tsx
import React, { useState } from 'react';
import Header from './components/Header';
import Pricer from './components/Pricer';

const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<string>('pricer');

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      <Header currentPage={currentPage} setCurrentPage={setCurrentPage} />
      
      <main className="w-full">
        {currentPage === 'dashboard' && (
          <div className="w-full px-8 py-6">
            <h2 className="text-2xl font-bold text-white mb-2">Dashboard</h2>
            <p className="text-gray-400">Coming soon...</p>
          </div>
        )}
        {currentPage === 'pricer' && <Pricer />}
      </main>
    </div>
  );
};

export default App;