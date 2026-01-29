// Image Viewer Compare - Webview Script

(function() {
    // Configuration will be injected by the extension
    const config = window.imageViewerConfig;
    let currentIndex = 0;
    let language = 'en';
    
    const translations = {
        en: {
            viewerTitle: 'Image Viewer',
            prev: 'Previous',
            next: 'Next',
            current: 'Current',
            showMethodName: 'Show Method Name',
            showDescription: 'Show Description',
            showSampleName: 'Show Sample Name',
            showText: 'Show Sample Text',
            numRows: 'Rows',
            noSamples: 'No samples to display',
            imageNotFound: 'Image not found',
            textLabel: 'Text'
        },
        zh: {
            viewerTitle: '图片查看器',
            prev: '上一个',
            next: '下一个',
            current: '当前',
            showMethodName: '显示方法名称',
            showDescription: '显示描述',
            showSampleName: '显示样本名称',
            showText: '显示文本',
            numRows: '行数',
            noSamples: '没有可显示的样本',
            imageNotFound: '图片未找到',
            textLabel: '文本'
        }
    };
    
    function toggleLanguage() {
        language = language === 'en' ? 'zh' : 'en';
        updateLanguage();
        render();
    }
    
    function updateLanguage() {
        const t = translations[language];
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            if (t[key]) {
                el.textContent = t[key];
            }
        });
        document.getElementById('viewerTitle').textContent = t.viewerTitle;
    }
    
    function render() {
        const grid = document.getElementById('imageGrid');
        const numRows = parseInt(document.getElementById('numRows').value);
        const showMethodName = document.getElementById('showMethodName').checked;
        const showDescription = document.getElementById('showDescription').checked;
        const showSampleName = document.getElementById('showSampleName').checked;
        const showText = document.getElementById('showText').checked;
        
        const t = translations[language];
        
        if (config.samples.length === 0) {
            grid.innerHTML = '<div class="no-samples">' + t.noSamples + '</div>';
            return;
        }
        
        const endIndex = Math.min(currentIndex + numRows, config.samples.length);
        const samplesToShow = config.samples.slice(currentIndex, endIndex);
        
        let html = '';
        
        samplesToShow.forEach((sample, idx) => {
            html += '<div class="sample-row">';
            
            if (showSampleName || (showText && sample.text)) {
                html += '<div class="sample-header">';
                if (showSampleName) {
                    html += '<span class="sample-name">' + escapeHtml(sample.name) + '</span>';
                }
                html += '</div>';
                if (showText && sample.text) {
                    html += '<div class="sample-text">' + t.textLabel + ': ' + escapeHtml(sample.text) + '</div>';
                }
            }
            
            html += '<div class="images-container">';
            
            config.methods.forEach(method => {
                const imageUri = sample.images[method.name];
                html += '<div class="image-card">';
                
                if (showMethodName) {
                    html += '<div class="method-name">' + escapeHtml(method.name) + '</div>';
                }
                if (showDescription && method.description) {
                    html += '<div class="method-description">' + escapeHtml(method.description) + '</div>';
                }
                
                html += '<div class="image-wrapper">';
                if (imageUri) {
                    html += '<img src="' + imageUri + '" alt="' + escapeHtml(method.name) + '" loading="lazy">';
                } else {
                    html += '<div class="image-error">' + t.imageNotFound + '</div>';
                }
                html += '</div>';
                
                html += '</div>';
            });
            
            html += '</div>';
            html += '</div>';
        });
        
        grid.innerHTML = html;
        updateNavigation();
    }
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    function prevSample() {
        const numRows = parseInt(document.getElementById('numRows').value);
        if (currentIndex > 0) {
            currentIndex = Math.max(0, currentIndex - numRows);
            render();
        }
    }
    
    function nextSample() {
        const numRows = parseInt(document.getElementById('numRows').value);
        if (currentIndex + numRows < config.samples.length) {
            currentIndex += numRows;
            render();
        }
    }
    
    function updateNavigation() {
        const numRows = parseInt(document.getElementById('numRows').value);
        document.getElementById('prevBtn').disabled = currentIndex === 0;
        document.getElementById('nextBtn').disabled = currentIndex + numRows >= config.samples.length;
        document.getElementById('currentIndex').textContent = currentIndex + 1;
        document.getElementById('totalSamples').textContent = config.samples.length;
    }
    
    // Expose functions to global scope for onclick handlers
    window.toggleLanguage = toggleLanguage;
    window.prevSample = prevSample;
    window.nextSample = nextSample;
    window.render = render;
    
    // Initial render
    render();
})();
