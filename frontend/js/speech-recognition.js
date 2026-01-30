/**
 * Speech Recognition Module for Reading Practice
 * Uses Web Speech API for Turkish speech-to-text
 */

class SpeechRecognitionPractice {
    constructor() {
        this.recognition = null;
        this.isRecording = false;
        this.transcript = '';
        this.onResultCallback = null;
        this.onErrorCallback = null;
        this.onEndCallback = null;
        this.interimTranscript = '';

        this.init();
    }

    /**
     * Initialize Speech Recognition
     */
    init() {
        // Check browser support
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
            console.error('Speech Recognition not supported in this browser');
            return false;
        }

        this.recognition = new SpeechRecognition();

        // Configure for Turkish
        this.recognition.lang = 'tr-TR';
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.maxAlternatives = 1;

        // Event handlers
        this.recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript + ' ';
                } else {
                    interimTranscript += transcript;
                }
            }

            if (finalTranscript) {
                this.transcript += finalTranscript;
            }
            this.interimTranscript = interimTranscript;

            if (this.onResultCallback) {
                this.onResultCallback({
                    final: this.transcript.trim(),
                    interim: this.interimTranscript,
                    combined: (this.transcript + this.interimTranscript).trim()
                });
            }
        };

        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            if (this.onErrorCallback) {
                this.onErrorCallback(event.error);
            }
        };

        this.recognition.onend = () => {
            this.isRecording = false;
            if (this.onEndCallback) {
                this.onEndCallback(this.transcript.trim());
            }
        };

        return true;
    }

    /**
     * Check if browser supports Speech Recognition
     */
    static isSupported() {
        return !!(window.SpeechRecognition || window.webkitSpeechRecognition);
    }

    /**
     * Request microphone permission
     */
    async requestMicrophonePermission() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            stream.getTracks().forEach(track => track.stop());
            return true;
        } catch (error) {
            console.error('Microphone permission denied:', error);
            return false;
        }
    }

    /**
     * Start recording
     */
    async start() {
        if (!this.recognition) {
            throw new Error('Speech Recognition not initialized');
        }

        const hasPermission = await this.requestMicrophonePermission();
        if (!hasPermission) {
            throw new Error('Microphone permission denied');
        }

        this.transcript = '';
        this.interimTranscript = '';
        this.isRecording = true;
        this.recognition.start();
    }

    /**
     * Stop recording
     */
    stop() {
        if (this.recognition && this.isRecording) {
            this.recognition.stop();
            this.isRecording = false;
        }
        return this.transcript.trim();
    }

    /**
     * Set callback for results
     */
    onResult(callback) {
        this.onResultCallback = callback;
    }

    /**
     * Set callback for errors
     */
    onError(callback) {
        this.onErrorCallback = callback;
    }

    /**
     * Set callback for end
     */
    onEnd(callback) {
        this.onEndCallback = callback;
    }
}

/**
 * Text comparison utility for reading error detection
 */
class TextComparator {
    /**
     * Normalize text for comparison
     */
    static normalize(text) {
        return text
            .toLowerCase()
            .replace(/[.,!?;:'"()\[\]{}]/g, '') // Remove punctuation
            .replace(/\s+/g, ' ') // Normalize whitespace
            .trim();
    }

    /**
     * Split text into words
     */
    static tokenize(text) {
        return this.normalize(text).split(' ').filter(word => word.length > 0);
    }

    /**
     * Calculate Levenshtein distance between two strings
     */
    static levenshteinDistance(str1, str2) {
        const m = str1.length;
        const n = str2.length;
        const dp = Array(m + 1).fill(null).map(() => Array(n + 1).fill(0));

        for (let i = 0; i <= m; i++) dp[i][0] = i;
        for (let j = 0; j <= n; j++) dp[0][j] = j;

        for (let i = 1; i <= m; i++) {
            for (let j = 1; j <= n; j++) {
                if (str1[i - 1] === str2[j - 1]) {
                    dp[i][j] = dp[i - 1][j - 1];
                } else {
                    dp[i][j] = 1 + Math.min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]);
                }
            }
        }
        return dp[m][n];
    }

    /**
     * Calculate similarity ratio between two words (0-1)
     */
    static similarity(word1, word2) {
        const maxLen = Math.max(word1.length, word2.length);
        if (maxLen === 0) return 1;
        const distance = this.levenshteinDistance(word1, word2);
        return 1 - (distance / maxLen);
    }

    /**
     * Compare original text with spoken text using fuzzy matching
     * Returns detailed comparison results
     */
    static compare(originalText, spokenText, similarityThreshold = 0.70) {
        const originalWords = this.tokenize(originalText);
        const spokenWords = this.tokenize(spokenText);

        const results = {
            originalWords: originalWords,
            spokenWords: spokenWords,
            wordResults: [],
            correctCount: 0,
            incorrectCount: 0,
            missedCount: 0,
            extraCount: 0,
            accuracy: 0
        };

        // Track which spoken words have been used
        const usedSpokenIndices = new Set();

        // For each original word, find the best matching spoken word
        for (let i = 0; i < originalWords.length; i++) {
            const originalWord = originalWords[i];
            let bestMatch = null;
            let bestSimilarity = 0;
            let bestIndex = -1;

            // Search in a window around the expected position
            const searchStart = Math.max(0, i - 5);
            const searchEnd = Math.min(spokenWords.length, i + 10);

            for (let j = searchStart; j < searchEnd; j++) {
                if (usedSpokenIndices.has(j)) continue;

                const spokenWord = spokenWords[j];
                const sim = this.similarity(originalWord, spokenWord);

                // Prefer matches closer to expected position
                const positionBonus = 1 - (Math.abs(i - j) * 0.02);
                const adjustedSim = sim * positionBonus;

                if (adjustedSim > bestSimilarity) {
                    bestSimilarity = adjustedSim;
                    bestMatch = spokenWord;
                    bestIndex = j;
                }
            }

            // Also check exact match anywhere (for words that might be far)
            if (bestSimilarity < 0.9) {
                for (let j = 0; j < spokenWords.length; j++) {
                    if (usedSpokenIndices.has(j)) continue;
                    if (j >= searchStart && j < searchEnd) continue; // Already checked

                    const spokenWord = spokenWords[j];
                    if (spokenWord === originalWord) {
                        bestSimilarity = 1;
                        bestMatch = spokenWord;
                        bestIndex = j;
                        break;
                    }
                }
            }

            if (bestMatch && bestSimilarity >= similarityThreshold) {
                usedSpokenIndices.add(bestIndex);
                results.wordResults.push({
                    original: originalWord,
                    spoken: bestMatch,
                    status: 'correct',
                    similarity: bestSimilarity
                });
                results.correctCount++;
            } else if (bestMatch && bestSimilarity >= 0.5) {
                // Partial match - close but not quite
                usedSpokenIndices.add(bestIndex);
                results.wordResults.push({
                    original: originalWord,
                    spoken: bestMatch,
                    status: 'incorrect',
                    similarity: bestSimilarity
                });
                results.incorrectCount++;
            } else {
                // No good match found
                results.wordResults.push({
                    original: originalWord,
                    spoken: '',
                    status: 'missed',
                    similarity: 0
                });
                results.missedCount++;
            }
        }

        // Count extra words
        results.extraCount = Math.max(0, spokenWords.length - usedSpokenIndices.size);

        // Calculate accuracy
        if (originalWords.length > 0) {
            results.accuracy = Math.round((results.correctCount / originalWords.length) * 100);
        }

        return results;
    }

    /**
     * Generate HTML for displaying results
     */
    static generateResultHTML(comparisonResults) {
        let html = '<div class="word-comparison">';

        comparisonResults.wordResults.forEach(result => {
            const statusClass = `word-${result.status}`;
            const tooltip = result.status === 'incorrect'
                ? `Söylenen: "${result.spoken}"`
                : result.status === 'missed'
                    ? 'Bu kelime okunmadı'
                    : 'Doğru';

            html += `<span class="${statusClass}" title="${tooltip}">${result.original}</span> `;
        });

        html += '</div>';

        // Summary
        html += `
            <div class="result-summary">
                <div class="summary-item correct">
                    <i class="fas fa-check-circle"></i>
                    <span>Doğru: ${comparisonResults.correctCount}</span>
                </div>
                <div class="summary-item incorrect">
                    <i class="fas fa-times-circle"></i>
                    <span>Hatalı: ${comparisonResults.incorrectCount}</span>
                </div>
                <div class="summary-item missed">
                    <i class="fas fa-minus-circle"></i>
                    <span>Atlanmış: ${comparisonResults.missedCount}</span>
                </div>
                <div class="summary-item accuracy">
                    <i class="fas fa-percentage"></i>
                    <span>Doğruluk: %${comparisonResults.accuracy}</span>
                </div>
            </div>
        `;

        return html;
    }
}

// Export for use
window.SpeechRecognitionPractice = SpeechRecognitionPractice;
window.TextComparator = TextComparator;
