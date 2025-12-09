import React from 'react';
import { Calendar, Smile, Frown, Meh, Users } from 'lucide-react';

const SeasonInsights = ({ data }) => {
    // 1. If no data is passed yet, render nothing or a placeholder
    if (!data) return null;

    // 2. Destructure the JSON response structure
    const { overview, top_10_events } = data;

    const top_events = top_10_events.slice(0, 5);

    // Safety check: ensure overview exists to prevent crashes
    if (!overview || !top_10_events) return <div className="card">No seasonal data available.</div>;

    return (
        <div style={{ paddingBottom: '2rem', marginTop: '2rem' }}>
            {/* Header */}
            <div style={{ marginBottom: '1.5rem' }}>
                <h3 style={{ fontSize: '1.25rem', fontWeight: '600', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span>🎉</span> Seasonal Event Insights
                </h3>
                <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    Analysis of specific events and festivals based on current filters.
                </p>
            </div>

            {/* Overview Stats */}
            <div className="stats-grid-4">
                <StatCard
                    title="Total Responses"
                    value={overview.total_responses || 0}
                    subtext=""
                    icon={Users}
                    color="#3b82f6"
                />
                <StatCard
                    title="Positive Sentiment"
                    value={overview.sentiment_breakdown?.positive_count || 0}
                    subtext={`${overview.sentiment_breakdown?.positive_percentage?.toFixed(1) || 0}% of Total`}
                    icon={Smile}
                    color="#10b981"
                />
                <StatCard
                    title="Negative Sentiment"
                    value={overview.sentiment_breakdown?.negative_count || 0}
                    subtext={`${overview.sentiment_breakdown?.negative_percentage?.toFixed(1) || 0}% of Total`}
                    icon={Frown}
                    color="#ef4444"
                />
                <StatCard
                    title="Neutral Sentiment"
                    value={overview.sentiment_breakdown?.neutral_count || 0}
                    subtext={`${overview.sentiment_breakdown?.neutral_percentage?.toFixed(1) || 0}% of Total`}
                    icon={Meh}
                    color="#f59e0b"
                />
            </div>

            {/* Top 10 Events Table */}
            <div className="card" style={{ marginTop: '2rem' }}>
                <div style={{ marginBottom: '1.5rem' }}>
                    <h3 style={{ fontSize: '1.1rem', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
                        Top Events & Festivals
                    </h3>
                </div>

                <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr style={{ borderBottom: '2px solid var(--border-color)' }}>
                                <th style={tableHeaderStyle}>Rank</th>
                                <th style={{ ...tableHeaderStyle, textAlign: 'left' }}>Event Name</th>
                                <th style={tableHeaderStyle}>Responses</th>
                                <th style={tableHeaderStyle}>Positive</th>
                                <th style={tableHeaderStyle}>Negative</th>
                                <th style={tableHeaderStyle}>Neutral</th>
                                <th style={tableHeaderStyle}>Avg Score</th>
                                <th style={{ ...tableHeaderStyle, width: '200px' }}>Sentiment Distribution</th>
                            </tr>
                        </thead>
                        <tbody>
                            {top_events.map((event, index) => (
                                <EventRow key={index} event={event} rank={index + 1} />
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

// --- Sub-components (StatCard, EventRow, SentimentBar) ---

const StatCard = ({ title, value, subtext, icon: Icon, color }) => (
    <div className="card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
                <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>{title}</p>
                <h3 style={{ fontSize: '2rem', fontWeight: '700', color: 'var(--text-primary)' }}>{value}</h3>
            </div>
            <div style={{ width: '48px', height: '48px', borderRadius: '12px', backgroundColor: `${color}20`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Icon size={24} color={color} />
            </div>
        </div>
        <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{subtext}</p>
    </div>
);

const EventRow = ({ event, rank }) => {
    const { event_name, total_responses, sentiment_breakdown, avg_sentiment_score } = event;
    const { positive_count, negative_count, neutral_count, positive_percentage, negative_percentage, neutral_percentage } = sentiment_breakdown;

    // Helper to truncate long event names
    const displayName = event_name.length > 60 ? event_name.substring(0, 60) + '...' : event_name;

    return (
        <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
            <td style={tableCellStyle}>
                <div style={{ width: '32px', height: '32px', borderRadius: '50%', backgroundColor: rank <= 3 ? '#3b82f620' : 'var(--bg-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: '600', fontSize: '0.875rem', color: rank <= 3 ? '#3b82f6' : 'var(--text-secondary)' }}>
                    {rank}
                </div>
            </td>
            <td style={{ ...tableCellStyle, textAlign: 'left' }} title={event_name}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Calendar size={16} color="var(--text-secondary)" style={{ flexShrink: 0 }} />
                    <span style={{ fontWeight: '500', color: 'var(--text-primary)' }}>{displayName}</span>
                </div>
            </td>
            <td style={tableCellStyle}><span style={{ fontWeight: '600' }}>{total_responses}</span></td>
            <td style={tableCellStyle}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <span style={{ fontWeight: '600', color: '#10b981' }}>{positive_count}</span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>({positive_percentage?.toFixed(1)}%)</span>
                </div>
            </td>
            <td style={tableCellStyle}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <span style={{ fontWeight: '600', color: '#ef4444' }}>{negative_count}</span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>({negative_percentage?.toFixed(1)}%)</span>
                </div>
            </td>
            <td style={tableCellStyle}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <span style={{ fontWeight: '600', color: '#f59e0b' }}>{neutral_count}</span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>({neutral_percentage?.toFixed(1)}%)</span>
                </div>
            </td>
            <td style={tableCellStyle}>
                <span style={{ padding: '0.25rem 0.75rem', borderRadius: '12px', fontSize: '0.875rem', fontWeight: '600', backgroundColor: avg_sentiment_score >= 6 ? '#10b98120' : avg_sentiment_score >= 4 ? '#f59e0b20' : '#ef444420', color: avg_sentiment_score >= 6 ? '#10b981' : avg_sentiment_score >= 4 ? '#f59e0b' : '#ef4444' }}>
                    {avg_sentiment_score?.toFixed(2) || 'N/A'}
                </span>
            </td>
            <td style={tableCellStyle}>
                <SentimentBar positive={positive_percentage} negative={negative_percentage} neutral={neutral_percentage} />
            </td>
        </tr>
    );
};

const SentimentBar = ({ positive, negative, neutral }) => (
    <div style={{ width: '100%' }}>
        <div style={{ display: 'flex', height: '24px', borderRadius: '12px', overflow: 'hidden', backgroundColor: 'var(--bg-secondary)' }}>
            {positive > 0 && <div style={{ width: `${positive}%`, backgroundColor: '#10b981' }} />}
            {neutral > 0 && <div style={{ width: `${neutral}%`, backgroundColor: '#f59e0b' }} />}
            {negative > 0 && <div style={{ width: `${negative}%`, backgroundColor: '#ef4444' }} />}
        </div>
    </div>
);

const tableHeaderStyle = { padding: '1rem', textAlign: 'center', fontSize: '0.75rem', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' };
const tableCellStyle = { padding: '1rem', textAlign: 'center', fontSize: '0.875rem', color: 'var(--text-primary)' };

export default SeasonInsights;