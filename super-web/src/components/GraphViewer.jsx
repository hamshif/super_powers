
import React, { useEffect, useRef, useState } from 'react';
import { Network } from 'vis-network';
import 'vis-network/styles/vis-network.css';

const GraphViewer = ({ center, onClose }) => {
    const containerRef = useRef(null);
    const configRef = useRef(null);
    const networkRef = useRef(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

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
        <div className="graph-viewer-layout" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
            {/* Graph Area */}
            <div
                ref={containerRef}
                className="graph-canvas"
                style={{ flex: 1, minHeight: 0, position: 'relative', overflow: 'hidden', outline: 'none' }}
            >
                {/* Network renders here */}
            </div>

            {/* Control Panel (Rendered by Vis into this div) */}
            <div
                ref={configRef}
                className="vis-configuration-wrapper"
                style={{
                    height: '35vh',
                    width: '100%',
                    boxSizing: 'border-box',
                    flex: 'none',
                    overflowY: 'auto',
                    userSelect: 'none',
                    overscrollBehavior: 'contain'
                }}
            />
        </div>
    );
};

export default GraphViewer;
