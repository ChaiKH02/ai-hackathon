import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Users, PieChart, Settings, FileText, Activity } from 'lucide-react';

const Sidebar = () => {
    return (
        <aside className="sidebar">
            <div className="sidebar-logo">
                InsightDash
            </div>
            <nav className="nav-links">
                <NavLink
                    to="/dashboard"
                    className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                    style={{ textDecoration: 'none' }}
                >
                    <LayoutDashboard size={20} />
                    <span>Dashboard</span>
                </NavLink>


                <NavLink
                    to="/actions"
                    className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                    style={{ textDecoration: 'none' }}
                >
                    <Activity size={20} />
                    <span>Actions Log</span>
                </NavLink>


                <NavLink
                    to="/recommendations"
                    className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                    style={{ textDecoration: 'none' }}
                >
                    <PieChart size={20} />
                    <span>Recommendations</span>
                </NavLink>

                {/*
                <NavLink 
                    to="/surveys" 
                    className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                    style={{ textDecoration: 'none' }}
                >
                    <FileText size={20} />
                    <span>Surveys</span>
                </NavLink>
                */}

                <div style={{ flex: 1 }}></div>
                <div className="nav-item">
                    <Settings size={20} />
                    <span>Settings</span>
                </div>
            </nav>
        </aside>
    );
};

export default Sidebar;
