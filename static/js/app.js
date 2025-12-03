// ProctGuard Application JavaScript

// Global variables
let globalSocket = null;
let isMonitoringActive = false;

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize notifications
    initializeNotifications();
    
    // Initialize auto-refresh for admin dashboard
    if (window.location.pathname.includes('/admin')) {
        initializeAutoRefresh();
    }
}

function initializeTooltips() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

function initializeNotifications() {
    // Request notification permission
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
}

function initializeAutoRefresh() {
    // Auto-refresh admin dashboard every 30 seconds
    setInterval(() => {
        if (document.hidden) return; // Don't refresh if tab is hidden
        
        const currentPath = window.location.pathname;
        if (currentPath === '/admin' && !document.querySelector('.modal.show')) {
            // Only refresh if no modals are open
            refreshDashboardData();
        }
    }, 30000);
}

function refreshDashboardData() {
    // Add subtle loading indicator
    const refreshBtn = document.querySelector('[onclick="refreshData()"]');
    if (refreshBtn) {
        refreshBtn.innerHTML = '<i class="fas fa-sync-alt fa-spin"></i> Refreshing...';
        refreshBtn.disabled = true;
    }
    
    // Reload page after short delay
    setTimeout(() => {
        window.location.reload();
    }, 500);
}

// Notification functions
function showNotification(title, message, type = 'info') {
    // Browser notification
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(title, {
            body: message,
            icon: '/static/favicon.ico',
            tag: 'proctguard-notification'
        });
    }
    
    // In-app notification
    showToast(message, type);
}

function showToast(message, type = 'info') {
    const toastContainer = getOrCreateToastContainer();
    
    const toastId = 'toast-' + Date.now();
    const iconClass = getIconForType(type);
    const bgClass = getBgClassForType(type);
    
    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center text-white ${bgClass} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    <i class="${iconClass}"></i> ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { delay: 5000 });
    toast.show();
    
    // Remove element after it's hidden
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

function getOrCreateToastContainer() {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }
    return container;
}

function getIconForType(type) {
    switch (type) {
        case 'success': return 'fas fa-check-circle';
        case 'error': case 'danger': return 'fas fa-exclamation-circle';
        case 'warning': return 'fas fa-exclamation-triangle';
        default: return 'fas fa-info-circle';
    }
}

function getBgClassForType(type) {
    switch (type) {
        case 'success': return 'bg-success';
        case 'error': case 'danger': return 'bg-danger';
        case 'warning': return 'bg-warning';
        default: return 'bg-primary';
    }
}

// Utility functions
function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = seconds % 60;
    
    if (hours > 0) {
        return `${hours}h ${minutes}m ${remainingSeconds}s`;
    } else if (minutes > 0) {
        return `${minutes}m ${remainingSeconds}s`;
    } else {
        return `${remainingSeconds}s`;
    }
}

function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString();
}

function downloadFile(filename, content, mimeType = 'text/plain') {
    const element = document.createElement('a');
    const file = new Blob([content], { type: mimeType });
    element.href = URL.createObjectURL(file);
    element.download = filename;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
}

// Data export functions
function exportSessionData(sessionId) {
    fetch(`/api/export_session/${sessionId}`)
        .then(response => response.json())
        .then(data => {
            const csvContent = convertToCSV(data);
            downloadFile(`session_${sessionId}_report.csv`, csvContent, 'text/csv');
            showToast('Session data exported successfully!', 'success');
        })
        .catch(error => {
            console.error('Export error:', error);
            showToast('Failed to export session data.', 'error');
        });
}

function convertToCSV(data) {
    if (!data || data.length === 0) return '';
    
    const headers = Object.keys(data[0]);
    const csvRows = [headers.join(',')];
    
    for (const row of data) {
        const values = headers.map(header => {
            const value = row[header];
            return typeof value === 'string' ? `"${value.replace(/"/g, '""')}"` : value;
        });
        csvRows.push(values.join(','));
    }
    
    return csvRows.join('\n');
}

// Camera and media utilities
class MediaHandler {
    constructor() {
        this.videoStream = null;
        this.audioStream = null;
        this.isRecording = false;
    }
    
    async initializeCamera(videoElement) {
        try {
            this.videoStream = await navigator.mediaDevices.getUserMedia({
                video: { width: 640, height: 480 },
                audio: false
            });
            
            if (videoElement) {
                videoElement.srcObject = this.videoStream;
            }
            
            return true;
        } catch (error) {
            console.error('Camera initialization failed:', error);
            throw error;
        }
    }
    
    async initializeAudio() {
        try {
            this.audioStream = await navigator.mediaDevices.getUserMedia({
                audio: true,
                video: false
            });
            
            return true;
        } catch (error) {
            console.error('Audio initialization failed:', error);
            throw error;
        }
    }
    
    captureFrame(videoElement) {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        canvas.width = videoElement.videoWidth;
        canvas.height = videoElement.videoHeight;
        
        ctx.drawImage(videoElement, 0, 0);
        
        return canvas.toDataURL('image/jpeg', 0.8);
    }
    
    stopAllStreams() {
        if (this.videoStream) {
            this.videoStream.getTracks().forEach(track => track.stop());
            this.videoStream = null;
        }
        
        if (this.audioStream) {
            this.audioStream.getTracks().forEach(track => track.stop());
            this.audioStream = null;
        }
    }
}

// Global media handler instance
const mediaHandler = new MediaHandler();

// Socket.IO utilities
function initializeSocket(namespace = '') {
    const socket = io(namespace);
    
    socket.on('connect', () => {
        console.log('Connected to server');
        showToast('Connected to monitoring server', 'success');
    });
    
    socket.on('disconnect', () => {
        console.log('Disconnected from server');
        showToast('Disconnected from server', 'warning');
    });
    
    socket.on('error', (error) => {
        console.error('Socket error:', error);
        showToast('Connection error occurred', 'error');
    });
    
    return socket;
}

// Form validation utilities
function validateForm(formElement) {
    const requiredFields = formElement.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('is-invalid');
            isValid = false;
        } else {
            field.classList.remove('is-invalid');
        }
    });
    
    return isValid;
}

// Local storage utilities
const Storage = {
    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (error) {
            console.warn('Failed to save to localStorage:', error);
        }
    },
    
    get(key, defaultValue = null) {
        try {
            const value = localStorage.getItem(key);
            return value ? JSON.parse(value) : defaultValue;
        } catch (error) {
            console.warn('Failed to read from localStorage:', error);
            return defaultValue;
        }
    },
    
    remove(key) {
        try {
            localStorage.removeItem(key);
        } catch (error) {
            console.warn('Failed to remove from localStorage:', error);
        }
    }
};

// Performance monitoring
const Performance = {
    mark(name) {
        if ('performance' in window) {
            performance.mark(name);
        }
    },
    
    measure(name, startMark, endMark) {
        if ('performance' in window) {
            try {
                performance.measure(name, startMark, endMark);
                const measure = performance.getEntriesByName(name)[0];
                console.log(`${name}: ${measure.duration.toFixed(2)}ms`);
                return measure.duration;
            } catch (error) {
                console.warn('Performance measurement failed:', error);
            }
        }
        return 0;
    }
};

// Error handling
window.addEventListener('error', function(event) {
    console.error('Global error:', event.error);
    
    // Don't show toast for every error to avoid spam
    if (event.error && event.error.message) {
        console.error('Application error:', event.error.message);
    }
});

window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
});

// Export for use in other scripts
window.ProctGuard = {
    showNotification,
    showToast,
    formatDuration,
    formatTimestamp,
    downloadFile,
    exportSessionData,
    mediaHandler,
    initializeSocket,
    validateForm,
    Storage,
    Performance
};