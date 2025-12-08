import React, { useState, useEffect } from 'react';
import { Clock, CheckCircle, AlertTriangle, Activity, Calendar } from 'lucide-react';
import './actions_log.css';
import API_URL from '../../config';

const ActionsLog = () => {
    const [actions, setActions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Filters State
    const [departments, setDepartments] = useState([]);
    const [selectedDepartment, setSelectedDepartment] = useState('All');
    const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
    const [selectedMonth, setSelectedMonth] = useState('All');

    // Constants
    const currentYear = new Date().getFullYear();
    const years = [currentYear, currentYear - 1, currentYear - 2, currentYear - 3, currentYear - 4];
    const months = [
        { value: 'All', label: 'All Months' },
        { value: 1, label: 'January' },
        { value: 2, label: 'February' },
        { value: 3, label: 'March' },
        { value: 4, label: 'April' },
        { value: 5, label: 'May' },
        { value: 6, label: 'June' },
        { value: 7, label: 'July' },
        { value: 8, label: 'August' },
        { value: 9, label: 'September' },
        { value: 10, label: 'October' },
        { value: 11, label: 'November' },
        { value: 12, label: 'December' },
    ];

    // Fetch Departments
    useEffect(() => {
        const fetchDepartments = async () => {
            try {
                const response = await fetch(`${API_URL}/departments`);
                if (response.ok) {
                    const data = await response.json();
                    const deptList = data.map(item => typeof item === 'object' ? (item.Department_Name || item.Department_ID) : item).filter(Boolean);
                    setDepartments([...new Set(deptList)].sort());
                }
            } catch (err) {
                console.error("Error fetching departments:", err);
            }
        };
        fetchDepartments();
    }, []);

    // Fetch Actions
    useEffect(() => {
        const fetchActions = async () => {
            setLoading(true);
            try {
                const params = new URLSearchParams();
                if (selectedDepartment !== 'All') params.append('department', selectedDepartment);
                if (selectedYear !== 'All') params.append('year', selectedYear);
                if (selectedMonth !== 'All') params.append('month', selectedMonth);

                const response = await fetch(`${API_URL}/actions_log/all?${params.toString()}`);
                if (!response.ok) {
                    throw new Error('Failed to fetch actions');
                }
                const data = await response.json();
                setActions(data);
                setError(null);
            } catch (err) {
                console.error("Error fetching actions:", err);
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchActions();
    }, [selectedDepartment, selectedYear, selectedMonth]);

    if (error) {
        return (
            <div className="actions-log-container">
                <div style={{ color: 'var(--danger)', padding: '1rem', background: '#fee2e2', borderRadius: 'var(--radius)' }}>
                    Error: {error}
                </div>
            </div>
        );
    }

    return (
        <div className="actions-log-container">
            <div className="header-actions" style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                <h1 className="header-title" style={{ margin: 0 }}>Actions Log</h1>

                {/* Filters Bar */}
                <div className="filters-bar" style={{ display: 'flex', gap: '0.75rem' }}>

                    {/* Department Filter */}
                    <select
                        className="filter-select"
                        value={selectedDepartment}
                        onChange={(e) => setSelectedDepartment(e.target.value)}
                        style={{ padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--border)', fontSize: '0.875rem' }}
                    >
                        <option value="All">All Departments</option>
                        {departments.map((dept, idx) => (
                            <option key={idx} value={dept}>{dept}</option>
                        ))}
                    </select>

                    {/* Year Filter */}
                    <select
                        className="filter-select"
                        value={selectedYear}
                        onChange={(e) => setSelectedYear(e.target.value === 'All' ? 'All' : Number(e.target.value))}
                        style={{ padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--border)', fontSize: '0.875rem' }}
                    >
                        {years.map((year) => (
                            <option key={year} value={year}>{year}</option>
                        ))}
                        <option value="All">All Years</option>
                    </select>

                    {/* Month Filter */}
                    <select
                        className="filter-select"
                        value={selectedMonth}
                        onChange={(e) => setSelectedMonth(e.target.value === 'All' ? 'All' : Number(e.target.value))}
                        style={{ padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--border)', fontSize: '0.875rem' }}
                    >
                        {months.map((m) => (
                            <option key={m.value} value={m.value}>{m.label}</option>
                        ))}
                    </select>

                </div>
            </div>

            {loading ? (
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '40vh', color: 'var(--text-secondary)' }}>
                    Loading actions...
                </div>
            ) : (
                <>
                    <div className="actions-grid">
                        {actions.map((action) => (
                            <ActionCard
                                key={action.Action_ID}
                                action={action}
                                onUpdateStatus={async (newStatus) => {
                                    try {
                                        const response = await fetch(`${API_URL}/actions_log/update/${action.Action_ID}`, {
                                            method: 'PUT',
                                            headers: { 'Content-Type': 'application/json' },
                                            body: JSON.stringify({ Activity_status: newStatus })
                                        });
                                        if (response.ok) {
                                            // Update local state
                                            setActions(prev => prev.map(a =>
                                                a.Action_ID === action.Action_ID ? { ...a, Activity_status: newStatus } : a
                                            ));
                                        } else {
                                            console.error("Failed to update status");
                                        }
                                    } catch (err) {
                                        console.error("Error updating status:", err);
                                    }
                                }}
                            />
                        ))}
                    </div>

                    {actions.length === 0 && (
                        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)', background: 'var(--bg-light)', borderRadius: 'var(--radius)', marginTop: '1rem' }}>
                            No actions found for the selected filters.
                        </div>
                    )}
                </>
            )}
        </div>
    );
};

const ActionCard = ({ action, onUpdateStatus }) => {
    const {
        Activity_title,
        Description,
        Impact,
        Department,
        Activity_status,
        Assigned_to,
        Quarter,
        Year,
        Impact_Burnout,
        Impact_Turnover,
        Completed_at
    } = action;

    const getInitials = (name) => {
        if (!name) return '?';
        return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
    };

    const isPending = Activity_status === 'pending';
    const isOnGoing = Activity_status === 'on-going';
    const isCompleted = Activity_status === 'completed';
    const isCancelled = Activity_status === 'cancelled';

    return (
        <div className="action-card">
            <div className="action-card-header">
                <span className="department-badge">{Department}</span>
                <div className={`status-badge ${isCompleted ? 'status-completed' : isOnGoing ? 'status-ongoing' : isCancelled ? 'status-cancelled' : 'status-pending'}`}>
                    {isCompleted ? <CheckCircle size={12} /> :
                        isOnGoing ? <Activity size={12} /> :
                            isCancelled ? <AlertTriangle size={12} /> :
                                <Clock size={12} />}
                    {Activity_status}
                </div>
            </div>

            <div className="card-content">
                <h3 className="action-title">{Activity_title}</h3>
                <p className="action-description">{Description}</p>

                {Impact && (
                    <div className="impact-box">
                        <div className="impact-label">EXPECTED IMPACT</div>
                        <div className="impact-text">{Impact}</div>
                    </div>
                )}

                {isCompleted && (
                    <div style={{ display: 'flex', gap: '0.8rem', marginTop: '1rem', flexWrap: 'wrap' }}>
                        {(Impact_Burnout !== undefined && Impact_Burnout !== null) && (
                            <div className="risk-tag risk-high" title="Burnout Impact">
                                <Activity size={10} style={{ marginRight: '4px' }} />
                                Burnout: {Impact_Burnout}%
                            </div>
                        )}
                        {(Impact_Turnover !== undefined && Impact_Turnover !== null) && (
                            <div className="risk-tag risk-high" title="Turnover Impact">
                                <AlertTriangle size={10} style={{ marginRight: '4px' }} />
                                Turnover: {Impact_Turnover}%
                            </div>
                        )}
                        {Completed_at && (
                            <div className="risk-tag" title="Completed At" style={{ color: 'var(--success)', background: '#dcfce7' }}>
                                <CheckCircle size={10} style={{ marginRight: '4px' }} />
                                Done: {new Date(Completed_at).toLocaleDateString()}
                            </div>
                        )}
                    </div>
                )}
            </div>

            <div className="card-right-col">
                <div className="assignee">
                    <div className="assignee-avatar" title={Assigned_to}>
                        {getInitials(Assigned_to)}
                    </div>
                    <div className="assignee-details">
                        <span className="assignee-label">Assigned To</span>
                        <span className="assignee-name">{Assigned_to || 'Unassigned'}</span>
                    </div>
                </div>
                <div className="meta-info">
                    <div className="meta-row">
                        <Calendar size={12} />
                        {Quarter} {Year}
                    </div>
                </div>

                {/* Action Buttons */}
                {!isCompleted && !isCancelled && (
                    <div className="card-actions" style={{ display: 'flex', gap: '0.5rem', marginTop: 'auto' }}>
                        {/* Cancel Button - Show if pending or on-going */}
                        <button
                            className="btn-cancel"
                            onClick={() => onUpdateStatus('cancelled')}
                            title="Cancel Action"
                        >
                            Cancel
                        </button>

                        {/* Active Button - Show only if pending */}
                        {isPending && (
                            <button
                                className="btn-active"
                                onClick={() => onUpdateStatus('on-going')}
                                title="Mark as Active"
                            >
                                Active
                            </button>
                        )}
                    </div>
                )}
            </div>
        </div >
    );
};

export default ActionsLog;
