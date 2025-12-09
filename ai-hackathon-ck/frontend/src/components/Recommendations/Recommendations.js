import React, { useState, useEffect } from 'react';
import { Lightbulb, Target, Calendar, CheckCircle } from 'lucide-react';
import API_URL from '../../config';

const Recommendations = () => {
    const currentYear = new Date().getFullYear();
    const [selectedDept, setSelectedDept] = useState('');
    const [selectedQuarter, setSelectedQuarter] = useState('Q1');
    const [selectedYear, setSelectedYear] = useState(currentYear);
    const [departmentOptions, setDepartmentOptions] = useState([]);
    const [recommendations, setRecommendations] = useState(null);
    const [loading, setLoading] = useState(false);

    // Manager Assignment State
    const [managers, setManagers] = useState([]);
    const [showModal, setShowModal] = useState(false);
    const [selectedAction, setSelectedAction] = useState(null);
    const [selectedManager, setSelectedManager] = useState('');

    // Fetch Departments
    useEffect(() => {
        const fetchDepartments = async () => {
            try {
                const response = await fetch(`${API_URL}/departments`);
                const data = await response.json();

                // Helper to unmarshall DynamoDB JSON if needed (reused logic)
                const unmarshall = (item) => {
                    const newItem = {};
                    for (const key in item) {
                        const val = item[key];
                        if (val && typeof val === 'object') {
                            if (val.S !== undefined) newItem[key] = val.S;
                            else if (val.N !== undefined) newItem[key] = Number(val.N);
                            else newItem[key] = val; // Fallback
                        } else {
                            newItem[key] = val;
                        }
                    }
                    return newItem;
                };

                const processed = data.map(item => {
                    const values = Object.values(item);
                    const isDynamo = values.some(v => v && (v.S !== undefined || v.N !== undefined));
                    return isDynamo ? unmarshall(item) : item;
                });

                const deptNames = processed.map(d => d.Department_Name).filter(Boolean);
                const uniqueDepts = [...new Set(deptNames)];
                setDepartmentOptions(uniqueDepts);
                if (uniqueDepts.length > 0 && !selectedDept) {
                    setSelectedDept(uniqueDepts[0]);
                }
            } catch (error) {
                console.error("Failed to fetch departments", error);
            }
        };
        fetchDepartments();
    }, []);

    // Fetch Managers for the selected department
    useEffect(() => {
        if (!selectedDept) {
            setManagers([]);
            return;
        }
        const fetchManagers = async () => {
            try {
                const response = await fetch(`${API_URL}/manager?department=${selectedDept}`);
                if (response.ok) {
                    const data = await response.json();
                    setManagers(data);
                } else {
                    console.error("Failed to fetch managers");
                    setManagers([]);
                }
            } catch (error) {
                console.error("Error fetching managers:", error);
                setManagers([]);
            }
        };
        fetchManagers();
    }, [selectedDept]);

    // Fetch Recommendations
    const handleGenerate = async () => {
        if (!selectedDept || !selectedQuarter || !selectedYear) return;

        setLoading(true);
        try {
            const response = await fetch(`${API_URL}/recommendations/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    department: selectedDept,
                    quarter: selectedQuarter,
                    year: selectedYear
                }),
            });
            const data = await response.json();
            if (data.status === 'success') {
                setRecommendations(data.data);
            } else {
                console.error("Failed to generate recommendations", data);
            }
        } catch (error) {
            console.error("Error fetching recommendations:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleStartAction = (action) => {
        setSelectedAction(action);
        setShowModal(true);
        setSelectedManager('');
    };

    const handleConfirmAssignment = async () => {
        if (!selectedAction || !selectedManager || !recommendations) return;

        const manager = managers.find(m => m.Employee_ID === selectedManager);
        const managerName = manager ? manager.Name : 'Unknown';
        console.log(recommendations)
        const payload = {
            department: selectedDept,
            quarter: selectedQuarter,
            year: selectedYear,
            activity_type: selectedAction.activity_type,
            activity_status: 'pending',
            description: selectedAction.description,
            impact: selectedAction.impact || '',
            assigned_to: managerName,
            activity_title: selectedAction.title,
            context: {
                burnout_risk_percentage: recommendations?.burnout_risk_percentage,
                turnover_risk_percentage: recommendations?.turnover_risk_percentage
            }
        };

        try {
            const response = await fetch(`${API_URL}/actions_log/add`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });

            if (response.ok) {
                console.log(`Assigned action "${selectedAction.title}" to manager ${managerName}`);
                alert(`Action assigned successfully to ${managerName}!`);
                setShowModal(false);
                setSelectedAction(null);
                setSelectedManager('');
            } else {
                const errorData = await response.json();
                console.error("Failed to log action:", errorData);
                alert(`Failed to assign action: ${errorData.detail || 'Unknown error'}`);
            }
        } catch (error) {
            console.error("Error logging action:", error);
            alert("Error logging action. Please try again.");
        }
    };

    const quarters = ['Q1', 'Q2', 'Q3', 'Q4'];
    const years = Array.from({ length: 11 }, (_, i) => currentYear - i);

    return (
        <div style={{ paddingBottom: '2rem', position: 'relative' }}>
            {/* Modal Overlay */}
            {showModal && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    zIndex: 1000
                }}>
                    <div style={{
                        backgroundColor: 'var(--white)', padding: '2rem', borderRadius: 'var(--radius)',
                        width: '400px', maxWidth: '90%', boxShadow: 'var(--shadow-lg)'
                    }}>
                        <h3 style={{ marginTop: 0, marginBottom: '1rem' }}>Assign Action</h3>
                        <p style={{ marginBottom: '1rem', color: 'var(--text-secondary)' }}>
                            <strong>Action:</strong> {selectedAction?.title}
                        </p>

                        <div style={{ marginBottom: '1.5rem' }}>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: 500 }}>
                                Select Manager ({selectedDept})
                            </label>
                            <select
                                style={{ width: '100%', padding: '0.5rem', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}
                                value={selectedManager}
                                onChange={(e) => setSelectedManager(e.target.value)}
                            >
                                <option value="">-- Select a Manager --</option>
                                {managers.map(m => (
                                    <option key={m.Employee_ID} value={m.Employee_ID}>{m.Name} ({m.Role})</option>
                                ))}
                            </select>
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
                            <button
                                onClick={() => setShowModal(false)}
                                style={{ padding: '0.5rem 1rem', border: '1px solid var(--border)', background: 'transparent', borderRadius: 'var(--radius)', cursor: 'pointer' }}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleConfirmAssignment}
                                disabled={!selectedManager}
                                style={{
                                    padding: '0.5rem 1rem', border: 'none',
                                    backgroundColor: !selectedManager ? 'var(--text-secondary)' : 'var(--primary)',
                                    color: 'white', borderRadius: 'var(--radius)', cursor: !selectedManager ? 'not-allowed' : 'pointer'
                                }}
                            >
                                Confirm
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Filters */}
            <div className="filter-bar" style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '2rem' }}>
                <select
                    className="filter-select"
                    value={selectedDept}
                    onChange={(e) => setSelectedDept(e.target.value)}
                >
                    {departmentOptions.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
                <select
                    className="filter-select"
                    value={selectedQuarter}
                    onChange={(e) => setSelectedQuarter(e.target.value)}
                >
                    {quarters.map(q => <option key={q} value={q}>{q}</option>)}
                </select>
                <select
                    className="filter-select"
                    value={selectedYear}
                    onChange={(e) => setSelectedYear(e.target.value)}
                >
                    {years.map(y => <option key={y} value={y}>{y}</option>)}
                </select>
                <button
                    onClick={handleGenerate}
                    disabled={loading || !selectedDept}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        padding: '0.5rem 1rem',
                        backgroundColor: loading ? 'var(--text-secondary)' : 'var(--primary)',
                        color: 'white',
                        border: 'none',
                        borderRadius: 'var(--radius)',
                        cursor: loading ? 'not-allowed' : 'pointer',
                        fontSize: '0.875rem',
                        fontWeight: 500
                    }}
                >
                    {loading ? <Lightbulb size={16} className="spin" /> : <Lightbulb size={16} />}
                    {loading ? 'Generating...' : 'Generate Insights'}
                </button>
            </div>

            {loading ? (
                <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--text-secondary)' }}>
                    <p>Analyzing survey data and generating recommendations...</p>
                </div>
            ) : recommendations ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>

                    {/* Priority Actions */}
                    <Section title="Priority Actions" icon={CheckCircle}>
                        <div className="dashboard-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))' }}>
                            {recommendations.recommendations.priority_actions.map((action, idx) => (
                                <Card key={idx} title={action.action}>
                                    <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                                        <strong>Rationale:</strong> {action.rationale}
                                    </p>
                                    <div style={{ fontSize: '0.8rem', color: 'var(--primary)', fontWeight: 500, marginBottom: '1rem' }}>
                                        Timeline: {action.timeline}
                                    </div>
                                    <div style={{ marginTop: 'auto' }}>
                                        <button
                                            onClick={() => handleStartAction({
                                                title: action.action,
                                                description: action.action,
                                                impact: action.rationale,
                                                activity_type: 'actions'
                                            })}
                                            style={{ width: '100%', padding: '0.5rem', backgroundColor: 'var(--bg-light)', border: 'none', borderRadius: 'var(--radius)', cursor: 'pointer', fontWeight: 500, color: 'var(--primary)' }}
                                        >
                                            Start Action
                                        </button>
                                    </div>
                                </Card>
                            ))}
                        </div>
                    </Section>

                    {/* Recommended Events */}
                    <Section title="Recommended Events" icon={Calendar}>
                        <div className="dashboard-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))' }}>
                            {recommendations.recommendations.recommended_events.map((event, idx) => (
                                <Card key={idx} title={event.event}>
                                    <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                                        {event.description}
                                    </p>
                                    <div style={{ fontSize: '0.8rem', color: 'var(--success)', fontWeight: 500, marginBottom: '1rem' }}>
                                        Impact: {event.expected_impact}
                                    </div>
                                    <div style={{ marginTop: 'auto' }}>
                                        <button
                                            onClick={() => handleStartAction({
                                                title: event.event,
                                                description: event.description,
                                                impact: event.expected_impact,
                                                activity_type: 'events'
                                            })}
                                            style={{ width: '100%', padding: '0.5rem', backgroundColor: 'var(--bg-light)', border: 'none', borderRadius: 'var(--radius)', cursor: 'pointer', fontWeight: 500, color: 'var(--primary)' }}
                                        >
                                            Start Event
                                        </button>
                                    </div>
                                </Card>
                            ))}
                        </div>
                    </Section>

                    {/* Long Term Strategies */}
                    <Section title="Long Term Strategies" icon={Target}>
                        <div className="dashboard-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))' }}>
                            {recommendations.recommendations.long_term_strategies.map((strategy, idx) => (
                                <Card key={idx} title={strategy.strategy}>
                                    <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                                        {strategy.implementation}
                                    </p>
                                    <div style={{ marginTop: 'auto' }}>
                                        <button
                                            onClick={() => handleStartAction({
                                                title: strategy.strategy,
                                                description: strategy.strategy,
                                                impact: strategy.implementation,
                                                activity_type: 'long_term'
                                            })}
                                            style={{ width: '100%', padding: '0.5rem', backgroundColor: 'var(--bg-light)', border: 'none', borderRadius: 'var(--radius)', cursor: 'pointer', fontWeight: 500, color: 'var(--primary)' }}
                                        >
                                            Start Strategy
                                        </button>
                                    </div>
                                </Card>
                            ))}
                        </div>
                    </Section>

                </div>
            ) : (
                <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--text-secondary)', backgroundColor: 'var(--white)', borderRadius: 'var(--radius)', border: '1px dashed var(--border)' }}>
                    <Lightbulb size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
                    <p style={{ fontSize: '1.1rem', fontWeight: 500 }}>Ready to generate insights</p>
                    <p>Select a department, quarter, and year, then click "Generate Insights" to see AI-powered recommendations.</p>
                </div>
            )}
        </div>
    );
};

// Sub-components for internal use
const Section = ({ title, icon: Icon, children }) => (
    <div>
        <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.25rem', marginBottom: '1rem', color: 'var(--text-primary)' }}>
            <Icon size={24} color="var(--primary)" />
            {title}
        </h2>
        {children}
    </div>
);

const Card = ({ title, children }) => (
    <div className="card" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <h3 className="card-title" style={{ marginBottom: '0.75rem', fontSize: '1.1rem' }}>{title}</h3>
        {children}
    </div>
);

export default Recommendations;
