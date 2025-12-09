import React from 'react';
import Sidebar from './Sidebar';
import Header from './Header';

const MainLayout = ({ children }) => {
    return (
        <div className="app-container">
            <Sidebar />
            <div className="main-content">
                <Header />
                <main className="dashboard-scroll-area">
                    {children}
                </main>
            </div>
        </div>
    );
};

export default MainLayout;
