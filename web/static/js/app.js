/**
 * Article Editor Frontend JavaScript
 */

function articleEditor() {
    return {
        // State
        activeTab: 'editor',
        isDragging: false,
        isLoading: false,
        isProcessing: false,
        showComparison: false,
        
        // Data
        uploadedFile: null,
        processingOptions: {
            editingType: 'comprehensive',
            instructions: '',
            model: 'claude-3-5-sonnet-20241022',
            chunkSize: 15000,
            overlap: 500
        },
        
        processingStatus: {
            progress: 0,
            message: ''
        },
        
        processingResult: null,
        currentSessionId: null,
        websocket: null,
        sessions: [],
        originalText: '',
        editedText: '',
        
        defaultSettings: {
            chunkSize: 15000,
            overlap: 500
        },
        
        // Computed
        get estimatedTokens() {
            if (!this.uploadedFile?.file_info?.word_count) return 0;
            return Math.ceil(this.uploadedFile.file_info.word_count * 1.3);
        },
        
        get estimatedCost() {
            const tokens = this.estimatedTokens;
            if (!tokens) return 0;
            // Claude 3.5 Sonnet pricing: $3/1M input, $15/1M output
            const inputCost = (tokens / 1000000) * 3;
            const outputCost = (tokens / 1000000) * 15;
            return inputCost + outputCost;
        },
        
        // Lifecycle
        init() {
            this.loadSettings();
            this.loadSessions();
            this.updateInstructions();
        },
        
        // File handling
        handleFileDrop(event) {
            this.isDragging = false;
            const files = event.dataTransfer.files;
            if (files.length > 0) {
                this.uploadFile(files[0]);
            }
        },
        
        handleFileSelect(event) {
            const files = event.target.files;
            if (files.length > 0) {
                this.uploadFile(files[0]);
            }
        },
        
        async uploadFile(file) {
            this.isLoading = true;
            try {
                const formData = new FormData();
                formData.append('file', file);
                
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Upload failed');
                }
                
                this.uploadedFile = await response.json();
                this.showNotification('File uploaded successfully', 'success');
                
            } catch (error) {
                this.showNotification('Upload failed: ' + error.message, 'error');
                console.error('Upload error:', error);
            } finally {
                this.isLoading = false;
            }
        },
        
        clearFile() {
            this.uploadedFile = null;
            this.processingResult = null;
            this.currentSessionId = null;
            this.showComparison = false;
            if (this.websocket) {
                this.websocket.close();
                this.websocket = null;
            }
        },
        
        // Instructions
        updateInstructions() {
            const instructions = {
                comprehensive: `Please edit this text with the following guidelines:
- Fix grammar, punctuation, and spelling errors
- Improve sentence flow and readability
- Ensure consistent tone and style throughout
- Fix awkward phrasing and unclear expressions
- Maintain the original meaning and voice
- Preserve formatting markers (headers, lists, etc.)
- Make the text more engaging and professional while keeping the author's intent

Provide only the edited text without any explanatory comments.`,
                
                grammar: `Please edit this text focusing only on:
- Fix grammar errors
- Correct punctuation
- Fix spelling mistakes
- Maintain the original wording and style as much as possible

Provide only the edited text without any explanatory comments.`,
                
                style: `Please edit this text to improve style and readability:
- Improve sentence flow and rhythm
- Enhance word choice and vocabulary
- Ensure consistent tone throughout
- Make the writing more engaging
- Maintain the original meaning and voice

Provide only the edited text without any explanatory comments.`,
                
                clarity: `Please edit this text to improve clarity and flow:
- Fix unclear or confusing sentences
- Improve logical flow between ideas
- Ensure smooth transitions between paragraphs
- Make complex ideas easier to understand
- Maintain the original meaning and technical accuracy

Provide only the edited text without any explanatory comments.`
            };
            
            if (this.processingOptions.editingType !== 'custom') {
                this.processingOptions.instructions = instructions[this.processingOptions.editingType] || '';
            }
        },
        
        // Processing
        async startProcessing(previewOnly = false) {
            if (!this.uploadedFile) {
                this.showNotification('Please upload a file first', 'error');
                return;
            }
            
            this.isProcessing = true;
            this.processingResult = null;
            this.processingStatus = { progress: 0, message: 'Starting...' };
            
            try {
                const formData = new FormData();
                formData.append('file_id', this.uploadedFile.file_id);
                formData.append('filename', this.uploadedFile.filename);
                formData.append('instructions', this.processingOptions.instructions);
                formData.append('chunk_size', this.processingOptions.chunkSize);
                formData.append('overlap', this.processingOptions.overlap);
                formData.append('model', this.processingOptions.model);
                formData.append('preview_only', previewOnly);
                
                const response = await fetch('/api/process', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Processing failed');
                }
                
                const result = await response.json();
                this.currentSessionId = result.session_id;
                
                // Connect to WebSocket for real-time updates
                this.connectWebSocket(result.session_id);
                
            } catch (error) {
                this.isProcessing = false;
                this.showNotification('Processing failed: ' + error.message, 'error');
                console.error('Processing error:', error);
            }
        },
        
        connectWebSocket(sessionId) {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/${sessionId}`;
            
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
            
            this.websocket.onclose = () => {
                if (this.isProcessing) {
                    // Try to reconnect after a delay
                    setTimeout(() => {
                        if (this.isProcessing && this.currentSessionId) {
                            this.connectWebSocket(this.currentSessionId);
                        }
                    }, 2000);
                }
            };
        },
        
        handleWebSocketMessage(data) {
            switch (data.type) {
                case 'status_update':
                case 'progress_update':
                    this.processingStatus.progress = data.progress || 0;
                    this.processingStatus.message = data.message || '';
                    break;
                    
                case 'completion':
                    this.isProcessing = false;
                    this.processingResult = data.result;
                    this.processingStatus.progress = 100;
                    this.processingStatus.message = 'Processing completed!';
                    this.showNotification('Processing completed successfully!', 'success');
                    this.loadSessions(); // Refresh session list
                    break;
                    
                case 'error':
                    this.isProcessing = false;
                    this.showNotification('Processing failed: ' + data.error, 'error');
                    break;
            }
        },
        
        async downloadResult() {
            if (!this.currentSessionId) return;
            
            try {
                const response = await fetch(`/api/download/${this.currentSessionId}`);
                if (!response.ok) throw new Error('Download failed');
                
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${this.uploadedFile.filename}_edited.txt`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
            } catch (error) {
                this.showNotification('Download failed: ' + error.message, 'error');
            }
        },
        
        // Session management
        async loadSessions() {
            try {
                const response = await fetch('/api/sessions');
                if (response.ok) {
                    const data = await response.json();
                    this.sessions = data.sessions;
                }
            } catch (error) {
                console.error('Failed to load sessions:', error);
            }
        },
        
        async downloadSession(sessionId) {
            try {
                const response = await fetch(`/api/download/${sessionId}`);
                if (!response.ok) throw new Error('Download failed');
                
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `edited_document_${sessionId}.txt`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
            } catch (error) {
                this.showNotification('Download failed: ' + error.message, 'error');
            }
        },
        
        async deleteSession(sessionId) {
            if (!confirm('Are you sure you want to delete this session?')) return;
            
            try {
                const response = await fetch(`/api/sessions/${sessionId}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    this.sessions = this.sessions.filter(s => s.session_id !== sessionId);
                    this.showNotification('Session deleted', 'success');
                } else {
                    throw new Error('Delete failed');
                }
                
            } catch (error) {
                this.showNotification('Delete failed: ' + error.message, 'error');
            }
        },
        
        // Settings
        loadSettings() {
            const saved = localStorage.getItem('articleEditorSettings');
            if (saved) {
                const settings = JSON.parse(saved);
                this.defaultSettings = { ...this.defaultSettings, ...settings };
                this.processingOptions.chunkSize = this.defaultSettings.chunkSize;
                this.processingOptions.overlap = this.defaultSettings.overlap;
            }
        },
        
        saveSettings() {
            localStorage.setItem('articleEditorSettings', JSON.stringify(this.defaultSettings));
            this.showNotification('Settings saved', 'success');
        },
        
        // Utilities
        formatFileSize(bytes) {
            if (!bytes) return 'N/A';
            const units = ['B', 'KB', 'MB', 'GB'];
            let size = bytes;
            let unitIndex = 0;
            
            while (size >= 1024 && unitIndex < units.length - 1) {
                size /= 1024;
                unitIndex++;
            }
            
            return `${size.toFixed(1)} ${units[unitIndex]}`;
        },
        
        getStatusIcon(status) {
            const icons = {
                pending: 'fas fa-clock text-yellow-500',
                processing: 'fas fa-spinner fa-spin text-blue-500',
                completed: 'fas fa-check-circle text-green-500',
                failed: 'fas fa-exclamation-circle text-red-500'
            };
            return icons[status] || 'fas fa-question-circle text-gray-500';
        },
        
        showNotification(message, type = 'info') {
            // Simple notification system - could be enhanced with a proper toast library
            const colors = {
                success: 'bg-green-500',
                error: 'bg-red-500',
                info: 'bg-blue-500',
                warning: 'bg-yellow-500'
            };
            
            const notification = document.createElement('div');
            notification.className = `fixed top-4 right-4 ${colors[type]} text-white px-6 py-3 rounded-lg shadow-lg z-50 transition-opacity`;
            notification.textContent = message;
            
            document.body.appendChild(notification);
            
            setTimeout(() => {
                notification.style.opacity = '0';
                setTimeout(() => {
                    document.body.removeChild(notification);
                }, 300);
            }, 5000);
        }
    };
}