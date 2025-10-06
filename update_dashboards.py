#!/usr/bin/env python3
"""
Script to add Dark Mode and Excel/CSV export to dashboard HTML files
"""

import re
import os

# Dark mode CSS to add
DARK_MODE_CSS = """        .ripple { position: relative; overflow: hidden; }
        .ripple:active::after {
            content: ""; position: absolute; top: 50%; left: 50%; width: 100%; height: 100%;
            background: rgba(255,255,255,0.3); border-radius: 50%;
            transform: translate(-50%, -50%) scale(0); animation: ripple-animation 0.6s ease-out;
        }
        @keyframes ripple-animation { to { transform: translate(-50%, -50%) scale(2); opacity: 0; } }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
        .animate-fadeIn { animation: fadeIn 0.2s ease-out; }

        /* Dark Mode Styles */
        body.dark-mode { background: #1a202c; color: #e2e8f0; }
        body.dark-mode .bg-gray-50 { background: #1a202c; }
        body.dark-mode .bg-white { background: #2d3748; }
        body.dark-mode .text-gray-900 { color: #e2e8f0; }
        body.dark-mode .text-gray-700 { color: #cbd5e0; }
        body.dark-mode .text-gray-600 { color: #a0aec0; }
        body.dark-mode .text-gray-500 { color: #718096; }
        body.dark-mode .border-gray-200 { border-color: #4a5568; }
        body.dark-mode .material-card { box-shadow: 0 1px 3px rgba(0,0,0,0.3), 0 1px 2px rgba(0,0,0,0.24); }
        body.dark-mode .material-card:hover { box-shadow: 0 14px 28px rgba(0,0,0,0.4), 0 10px 10px rgba(0,0,0,0.3); }
        body.dark-mode .bg-gray-100 { background: #4a5568; }"""

# Common functions
COMMON_FUNCTIONS = """
        function toggleDarkMode() {
            document.body.classList.toggle('dark-mode');
            localStorage.setItem('darkMode', document.body.classList.contains('dark-mode'));
        }

        if (localStorage.getItem('darkMode') === 'true') {
            document.body.classList.add('dark-mode');
        }

        function ExportDropdown({ data }) {
            const [isOpen, setIsOpen] = useState(false);
            const dropdownRef = useRef(null);

            useEffect(() => {
                function handleClickOutside(event) {
                    if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                        setIsOpen(false);
                    }
                }
                document.addEventListener('mousedown', handleClickOutside);
                return () => document.removeEventListener('mousedown', handleClickOutside);
            }, []);

            return (
                <div className="relative" ref={dropdownRef}>
                    <button onClick={() => setIsOpen(!isOpen)} className="flex items-center gap-2 px-4 py-2 bg-white/20 hover:bg-white/30 text-white rounded-lg transition-all ripple">
                        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M19 12v7H5v-7H3v7c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2v-7h-2zm-6 .67l2.59-2.58L17 11.5l-5 5-5-5 1.41-1.41L11 12.67V3h2z"/>
                        </svg>
                        <span className="font-medium">Esporta</span>
                        <svg className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="currentColor" viewBox="0 0 20 20">
                            <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"/>
                        </svg>
                    </button>
                    {isOpen && (
                        <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-xl z-50 animate-fadeIn">
                            <button onClick={() => { exportToPDF(); setIsOpen(false); }} className="w-full text-left px-4 py-3 hover:bg-gray-100 text-gray-700 rounded-t-lg flex items-center gap-3 transition">
                                <svg className="w-5 h-5 text-red-500" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6z"/>
                                </svg>
                                <span className="font-medium">PDF</span>
                            </button>
                            <button onClick={() => { exportToExcel(data); setIsOpen(false); }} className="w-full text-left px-4 py-3 hover:bg-gray-100 text-gray-700 flex items-center gap-3 transition">
                                <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6z"/>
                                </svg>
                                <span className="font-medium">Excel (.xlsx)</span>
                            </button>
                            <button onClick={() => { exportToCSV(data); setIsOpen(false); }} className="w-full text-left px-4 py-3 hover:bg-gray-100 text-gray-700 rounded-b-lg flex items-center gap-3 transition">
                                <svg className="w-5 h-5 text-blue-500" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6z"/>
                                </svg>
                                <span className="font-medium">CSV</span>
                            </button>
                        </div>
                    )}
                </div>
            );
        }
"""

print("Dashboard update script created at: c:\\Progetti\\RAG\\update_dashboards.py")
print("This script provides templates for updating dashboard HTML files.")
