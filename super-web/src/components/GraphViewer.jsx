
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
    const [panelHeight, setPanelHeight] = useState(180); // 50% lower starting point (was 350)

    // --- RESIZE HANDLER ---
    const handleResizeMouseDown = (e) => {
        e.preventDefault();
        const startY = e.clientY;
        const startHeight = panelHeight;

        const onMouseMove = (moveEvent) => {
            const delta = startY - moveEvent.clientY; // Dragging UP increases height
            const newHeight = Math.max(100, Math.min(window.innerHeight * 0.8, startHeight + delta));
            setPanelHeight(newHeight);
        };

        const onMouseUp = () => {
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
            document.body.style.cursor = 'default';
        };

        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
        document.body.style.cursor = 'ns-resize';
    };

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

        // --- BUTTON INJECTOR (Insert Shrink Button into Vis Header) ---
        const injectToggle = () => {
            if (!configRef.current) return;
            const header = configRef.current.querySelector('.vis-config-header');

            if (header && !header.querySelector('.custom-shrink-btn')) {
                // Adjust Header Layout
                header.style.display = 'flex';
                header.style.justifyContent = 'flex-start';
                header.style.alignItems = 'center';
                header.style.paddingRight = '10px';

                // Create Container for Text (move text into span if needed, but flex handles text node)

                // Create Shrink Button
                const btn = document.createElement('div');
                btn.className = 'custom-shrink-btn';
                btn.title = "Shrink Panel";
                btn.style.cursor = 'pointer';
                btn.style.color = '#00f3ff';
                btn.style.display = 'flex';
                btn.style.alignItems = 'center';
                btn.style.marginRight = '10px';

                // Button Styling (Cyan Box)
                btn.style.border = '1px solid #00f3ff';
                btn.style.background = 'rgba(20, 22, 30, 0.5)';
                btn.style.padding = '4px';
                btn.style.borderRadius = '4px';

                // SVG Icon (Arrows In)
                btn.innerHTML = `
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#00f3ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="4 14 10 14 10 20"></polyline>
                        <polyline points="20 10 14 10 14 4"></polyline>
                        <line x1="14" y1="10" x2="21" y2="3"></line>
                        <line x1="3" y1="21" x2="10" y2="14"></line>
                    </svg>
                `;

                btn.onclick = (e) => {
                    e.stopPropagation();
                    setIsConfigOpen(false);
                };

                header.prepend(btn);
            }

            // Remove Empty Separator Logic (Nuclear DOM Cleanup)
            // Vis often puts an empty 'vis-config-s0' div before the header as a spacer/line.
            try {
                const parent = header?.parentElement; // The .vis-config-item wrapping the header
                if (parent) {
                    const prev = parent.previousElementSibling;
                    // Check if previous sibling is an empty s0 item
                    if (prev &&
                        prev.classList.contains('vis-config-s0') &&
                        prev.classList.contains('vis-config-item') &&
                        prev.innerText.trim() === ''
                    ) {
                        prev.style.display = 'none'; // Hide it
                        // or prev.remove(); 
                    }
                }
            } catch (e) {
                // Ignore cleanup errors
            }
        };

        // --- LAYOUT FLATTENER (Fix 2-Column Grid) ---
        // Vis-Network often wraps "Physics" options in a container div.
        // This forces Grid to put that whole container in Col 1.
        // We use display: contents to "unbox" it.
        const flattenLayout = () => {
            if (!configRef.current) return;
            // Select all direct children that might be wrappers
            // (i.e., not the header, and not a leaf item)
            const children = Array.from(configRef.current.children);
            children.forEach(child => {
                // Ignore Header and actual items
                if (child.classList.contains('vis-config-header') || child.classList.contains('vis-config-item')) {
                    return;
                }
                // If it's a generic div (likely a section wrapper), flatten it
                child.style.display = 'contents';
            });
        };

        const observer = new MutationObserver(() => {
            formatLabels();
            injectToggle();
            // flattenLayout();
        });
        observer.observe(configRef.current, { childList: true, subtree: true });

        // Initial run
        formatLabels();
        injectToggle();
        // flattenLayout();

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
            {/* --- STICKY FOOTER (Controls) --- */}
            <div style={{ position: 'sticky', bottom: 0, zIndex: 100, width: '100%' }}>

                {/* --- EXPAND BUTTON (OUTSIDE PANEL) --- */}
                {/* Renders only when panel is CLOSED */}
                {!isConfigOpen && (
                    <button
                        onClick={() => setIsConfigOpen(true)}
                        style={{
                            position: 'absolute',
                            bottom: '10px',
                            left: '10px', // Moved to right
                            zIndex: 1000,
                            background: 'rgba(20, 22, 30, 0.85)', // Dark backing
                            border: '1px solid #00f3ff', // Visible border when closed
                            color: '#00f3ff',
                            cursor: 'pointer',
                            padding: '6px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            borderRadius: '4px',
                            boxShadow: '0 0 10px rgba(0, 243, 255, 0.2)'
                        }}
                        title="Expand Physics Settings"
                    >
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="15 3 21 3 21 9" />
                            <polyline points="9 21 3 21 3 15" />
                            <line x1="21" y1="3" x2="14" y2="10" />
                            <line x1="3" y1="21" x2="10" y2="14" />
                        </svg>
                    </button>
                )}

                {/* --- RESIZE HANDLE --- */}
                {isConfigOpen && (
                    <div
                        onMouseDown={handleResizeMouseDown}
                        style={{
                            height: '10px',
                            width: '100%',
                            cursor: 'ns-resize',
                            background: 'transparent', // Looks like the line?
                            opacity: 0, // Force invisible
                            position: 'absolute',
                            top: '-5px',
                            zIndex: 101,
                        }}
                    />
                )}

                {/* --- CONFIG PANEL (EXPANDABLE) --- */}
                <div style={{
                    position: 'relative', // Context for absolute button
                    background: isConfigOpen ? 'rgba(20, 22, 30, 0.65)' : 'transparent',
                    border: 'none', // NUCLEAR: No borders allowed
                    outline: 'none',
                    boxShadow: 'none',
                    flexShrink: 0,
                    display: 'flex',
                    flexDirection: 'column',
                    transition: 'height 0.1s ease-out',
                    // Primary Toggle: Dynamic Height
                    height: isConfigOpen ? `${panelHeight}px` : '0px',
                    overflow: 'hidden' // Strict containment for scrollbars
                }}>
                    {/* Always rendered to keep Vis Interface alive */}
                    <div style={{
                        position: 'relative',
                        width: '100%',
                        height: '100%', // Strict height
                        overflow: 'auto', // PARENT SCROLLS
                        zIndex: 10
                    }}>

                        {/* Vis Config Content - WIDE CONTAINER */}
                        <div
                            ref={configRef}
                            className="vis-configuration-wrapper"
                            style={{
                                minWidth: '950px', // FORCE HORIZONTAL SCROLL
                                width: '100%',
                                height: 'auto', // Grow vertically

                                // Re-enable Grid (Color issue fixed globally)
                                // display: 'grid',
                                // gridTemplateColumns: 'minmax(450px, 1fr) minmax(450px, 1fr)',
                                // columnGap: '15px',

                                // display: 'block',
                                // columnCount: 2,
                                // columnGap: '20px',

                                boxSizing: 'border-box',
                                userSelect: 'none',
                                overscrollBehavior: 'contain',
                                paddingTop: '0px', // REMOVE GAP
                                paddingLeft: '0px', // REMOVE LEFT GAP
                                marginTop: '-1px', // OVERLAP PARENT BORDER
                                paddingBottom: '20px'
                            }}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default GraphViewer;
