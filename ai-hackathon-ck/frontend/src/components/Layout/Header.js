import React from 'react';
import { Bell, Search } from 'lucide-react';

const Header = () => {
    return (
        <header className="top-header">
            <h1 className="header-title">Employee Survey Dashboard</h1>
            <div className="header-actions">
                <div style={{ position: 'relative' }}>
                    <Bell size={20} color="var(--text-secondary)" style={{ cursor: 'pointer' }} />
                    <span style={{
                        position: 'absolute',
                        top: -2,
                        right: -2,
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        backgroundColor: 'var(--danger)'
                    }}></span>
                </div>
                <div className="user-profile">
                    <div className="avatar">JD</div>
                    <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>John Doe</span>
                </div>
            </div>
        </header>
    );
};

export default Header;
