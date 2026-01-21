
import React, { useEffect, useRef, useState } from 'react';
import { Network } from 'vis-network';
import 'vis-network/styles/vis-network.css';

const GraphViewer = ({ center, onClose }) => {
    const containerRef = useRef(null);
    const configRef = useRef(null);
    const networkRef = useRef(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [isConfigOpen, setIsConfigOpen] = useState(true);

    // MOCK DATA for Offline Layout Development
    const MOCK_DATA = {
        nodes: [
            { id: 'Superman', label: 'Superman', title: 'Start Node', group: 'Hero', color: '#ff9999' },
            { id: 'Flight', label: 'Flight', title: 'Power', group: 'Power', color: '#9999ff' },
            { id: 'Strength', label: 'Super Strength', title: 'Power', group: 'Power', color: '#9999ff' },
            { id: 'Krypton', label: 'Krypton', title: 'Planet', group: 'Seed', color: '#ffff99' },
            { id: 'Gene-X', label: 'Gene-X', title: 'Gene', group: 'Gene', color: '#99ff99' },
            { id: 'Gene-Y', label: 'Gene-Y', title: 'Gene', group: 'Gene', color: '#096e09ff' }
        ],
        edges: [
            { from: 'Superman', to: 'Flight' },
            { from: 'Superman', to: 'Strength' },
            { from: 'Superman', to: 'Krypton' },
            { from: 'Strength', to: 'Gene-X' },
            { from: 'Flight', to: 'Gene-Y' }
        ]
    };

    // Default Options (Dark Mode + Physics)
    const getOptions = (physicsEnabled, configContainer) => ({
        autoResize: true,
        height: '100%',
        width: '100%',
        clickToUse: false,
        nodes: {
            font: { color: '#e0e6ed', strokeWidth: 0, face: 'Inter' },
            shape: 'dot',
            size: 25
        },
        edges: {
            color: { color: '#ffffff', opacity: 0.2 },
            smooth: false
        },
        configure: {
            enabled: true,
            filter: ['physics'],
            container: configContainer, // Render controls HERE
            showButton: false
        },
        physics: {
            enabled: physicsEnabled,
            barnesHut: {
                theta: 0.15,
                gravitationalConstant: -3350,
                centralGravity: 0.3,
                springLength: 95,
                springConstant: 0.04,
                damping: 0.09,
                avoidOverlap: 0
            },
            solver: 'barnesHut',
            minVelocity: 0.07,
            timestep: 0.5
        }
    });

    useEffect(() => {
        if (!containerRef.current || !configRef.current) return;

        // Destroy previous network if exists
        if (networkRef.current) {
            try {
                networkRef.current.destroy();
            } catch (e) { console.warn("Cleanup error", e); }
        }

        // Clear config container to prevent duplicates (Strict Mode / Re-renders)
        if (configRef.current) {
            configRef.current.innerHTML = '';
        }

        // Always render with Mock Data immediately
        const usePhysics = true;

        // Create Network
        networkRef.current = new Network(
            containerRef.current,
            MOCK_DATA,
            getOptions(usePhysics, configRef.current)
        );

        // --- LABEL FORMATTER (Separate Compound Words) ---
        const formatLabels = () => {
            if (!configRef.current) return;
            const labels = configRef.current.querySelectorAll('.vis-config-label');
            labels.forEach(label => {
                if (label.dataset.formatted) return;

                const original = label.innerText;
                // gravitationalConstant -> Gravitational Constant
                const formatted = original
                    .replace(/([A-Z])/g, ' $1') // Space before capital
                    .replace(/^./, str => str.toUpperCase()) // Capitalize first
                    .trim();

                if (original !== formatted) {
                    label.innerText = formatted;
                    label.dataset.formatted = "true";
                }
            });
        };

        const observer = new MutationObserver(() => formatLabels());
        observer.observe(configRef.current, { childList: true, subtree: true });

        // Initial run
        formatLabels();

        return () => {
            observer.disconnect();
            if (networkRef.current) networkRef.current.destroy();
        };
    }, []); // Run once on mount, ignore 'center' prop for now

    return (
        <div className="graph-viewer-layout" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'auto' }}>
            {/* Graph Area */}
            <div
                ref={containerRef}
                className="graph-canvas"
                style={{ flex: 1, minHeight: '600px', position: 'relative', overflow: 'hidden', outline: 'none' }}
            >
                {/* Network renders here */}
            </div>

            {/* Control Panel (Rendered by Vis into this div) */}
            {/* Persistent Control Bar */}
            <div style={{
                background: 'rgba(20, 22, 30, 0.65)',
                borderTop: '1px solid #00f3ff',
                flexShrink: 0,
                display: 'flex',
                flexDirection: 'column'
            }}>
                {/* Toggle Button Row */}
                <div style={{
                    padding: '8px',
                    display: 'flex',
                    justifyContent: 'flex-start',
                    alignItems: 'center',
                    borderBottom: isConfigOpen ? '1px solid rgba(0, 243, 255, 0.2)' : 'none'
                }}>
                    <button
                        onClick={() => setIsConfigOpen(!isConfigOpen)}
                        style={{
                            background: 'transparent',
                            border: 'none',
                            color: '#00f3ff',
                            cursor: 'pointer',
                            padding: '4px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '8px',
                            fontFamily: "'JetBrains Mono', monospace",
                            fontSize: '0.9rem',
                            fontWeight: 'bold',
                            textTransform: 'uppercase'
                        }}
                    >
                        {isConfigOpen ? (
                            <>
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <polyline points="4 14 10 14 10 20" />
                                    <polyline points="20 10 14 10 14 4" />
                                    <line x1="14" y1="10" x2="21" y2="3" />
                                    <line x1="3" y1="21" x2="10" y2="14" />
                                </svg>
                                <span>Mask Config</span>
                            </>
                        ) : (
                            <>
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <polyline points="15 3 21 3 21 9" />
                                    <polyline points="9 21 3 21 3 15" />
                                    <line x1="21" y1="3" x2="14" y2="10" />
                                    <line x1="3" y1="21" x2="10" y2="14" />
                                </svg>
                                <span>Show Config</span>
                            </>
                        )}
                    </button>
                </div>

                {/* The actual Vis Config Panel (Collapsible) */}
                <div
                    ref={configRef}
                    className="vis-configuration-wrapper"
                    style={{
                        display: isConfigOpen ? 'grid' : 'none',
                        height: isConfigOpen ? '35vh' : '0px',
                        opacity: isConfigOpen ? 1 : 0,
                        width: '100%',
                        boxSizing: 'border-box',
                        overflowY: 'auto',
                        userSelect: 'none',
                        overscrollBehavior: 'contain',
                        transition: 'height 0.3s ease, opacity 0.3s ease'
                    }}
                />
            </div>
        </div>
    );
};

export default GraphViewer;
