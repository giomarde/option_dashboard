// src/components/Header.tsx
import React from 'react';

interface HeaderProps {
  currentPage: string;
  setCurrentPage: (page: string) => void;
}

const Header: React.FC<HeaderProps> = ({ currentPage, setCurrentPage }) => {
  return (
    <header className="bg-gray-800 border-b border-gray-700 sticky top-0 z-50 shadow-lg">
      <div className="w-full px-6 py-3">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
              Option Pricer
            </h1>
            <p className="text-gray-400 text-xs">Professional derivatives pricing platform</p>
          </div>
          
          <nav className="flex space-x-2">
            <button
              onClick={() => setCurrentPage('dashboard')}
              className={`px-6 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${
                currentPage === 'dashboard'
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/25'
                  : 'text-gray-300 hover:text-white hover:bg-gray-700'
              }`}
            >
              Dashboard
            </button>
            <button
              onClick={() => setCurrentPage('pricer')}
              className={`px-6 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${
                currentPage === 'pricer'
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/25'
                  : 'text-gray-300 hover:text-white hover:bg-gray-700'
              }`}
            >
              Pricer
            </button>
          </nav>
        </div>
      </div>
    </header>
  );
};

export default Header;