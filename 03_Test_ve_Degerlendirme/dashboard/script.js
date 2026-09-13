document.addEventListener("DOMContentLoaded", () => {
    // kiyaslamaVerileri comes from data.js
    let currentData = [...kiyaslamaVerileri];
    let currentPage = 1;
    const rowsPerPage = 50;

    // Elements
    const tableBody = document.getElementById('tableBody');
    const searchInput = document.getElementById('searchInput');
    const sortFilter = document.getElementById('sortFilter');
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    const pageInfo = document.getElementById('pageInfo');
    
    // Modal Elements
    const modal = document.getElementById('detailModal');
    const closeBtn = document.querySelector('.close-btn');
    const modalOrigTitle = document.getElementById('modal-orig-title');
    const modalOrigAbs = document.getElementById('modal-orig-abs');
    const modalOrigAuthors = document.getElementById('modal-orig-authors');
    const modalOrigKeywords = document.getElementById('modal-orig-keywords');
    const modalOrigExtra = document.getElementById('modal-orig-extra');

    const modalGrobTitle = document.getElementById('modal-grob-title');
    const modalGrobAbs = document.getElementById('modal-grob-abs');
    const modalGrobAuthors = document.getElementById('modal-grob-authors');
    const modalGrobKeywords = document.getElementById('modal-grob-keywords');
    const modalGrobExtra = document.getElementById('modal-grob-extra');

    // Init Summaries
    function initSummaries() {
        document.getElementById('total-articles').textContent = kiyaslamaVerileri.length;
        
        const matched = kiyaslamaVerileri.filter(item => item["Durum"] === "Eşleşti");
        let counts = { title: 0, abs: 0, author: 0, year: 0, journal: 0, doi: 0 };
        let sums = { title: 0, titlePrec: 0, abs: 0, absPrec: 0, author: 0, authorPrec: 0, year: 0, journal: 0, doi: 0 };
        
        matched.forEach(item => {
            if (item["Başlık Bulma Oranı (%)"] !== null) { sums.title += item["Başlık Bulma Oranı (%)"]; sums.titlePrec += item["Başlık Kesinlik Oranı (%)"]; counts.title++; }
            if (item["Özet Bulma Oranı (%)"] !== null) { sums.abs += item["Özet Bulma Oranı (%)"]; sums.absPrec += item["Özet Kesinlik Oranı (%)"]; counts.abs++; }
            if (item["Yazar Bulma Oranı (%)"] !== null) { sums.author += item["Yazar Bulma Oranı (%)"]; sums.authorPrec += item["Yazar Kesinlik Oranı (%)"]; counts.author++; }
            if (item["Yıl Başarı Oranı (%)"] !== null) { sums.year += item["Yıl Başarı Oranı (%)"]; counts.year++; }
            if (item["Dergi Başarı Oranı (%)"] !== null) { sums.journal += item["Dergi Başarı Oranı (%)"]; counts.journal++; }
            if (item["DOI Başarı Oranı (%)"] !== null) { sums.doi += item["DOI Başarı Oranı (%)"]; counts.doi++; }
        });

        const avgTitle = counts.title > 0 ? (sums.title / counts.title).toFixed(2) : 0;
        const avgTitlePrec = counts.title > 0 ? (sums.titlePrec / counts.title).toFixed(2) : 0;
        const avgAbs = counts.abs > 0 ? (sums.abs / counts.abs).toFixed(2) : 0;
        const avgAbsPrec = counts.abs > 0 ? (sums.absPrec / counts.abs).toFixed(2) : 0;
        const avgAuthor = counts.author > 0 ? (sums.author / counts.author).toFixed(2) : 0;
        const avgAuthorPrec = counts.author > 0 ? (sums.authorPrec / counts.author).toFixed(2) : 0;
        const avgYear = counts.year > 0 ? (sums.year / counts.year).toFixed(2) : 0;
        const avgJournal = counts.journal > 0 ? (sums.journal / counts.journal).toFixed(2) : 0;
        const avgDoi = counts.doi > 0 ? (sums.doi / counts.doi).toFixed(2) : 0;

        document.getElementById('avg-title-score').textContent = `${avgTitle}%`;
        document.getElementById('avg-title-prec').textContent = `${avgTitlePrec}%`;
        document.getElementById('avg-abstract-score').textContent = `${avgAbs}%`;
        document.getElementById('avg-abstract-prec').textContent = `${avgAbsPrec}%`;
        document.getElementById('avg-doi-score').textContent = `${avgDoi}%`;
        
        document.getElementById('avg-author-score').textContent = `${avgAuthor}%`;
        document.getElementById('avg-author-prec').textContent = `${avgAuthorPrec}%`;
        document.getElementById('avg-journal-score').textContent = `${avgJournal}%`;
        document.getElementById('avg-year-score').textContent = `${avgYear}%`;

        // Kapsam: metrik kac makale uzerinden hesaplandi. Bir alan TR Dizin
        // kaydinda bosa, o makale ortalamaya hic girmiyor -- yuzdeler ayni
        // paydaya dayanmiyor. Bunu gorunur kilmak icin kart icinde yaziyoruz.
        const toplam = kiyaslamaVerileri.length;
        const kapsamYaz = (id, adet) => {
            const el = document.getElementById(id);
            if (!el) return;
            const yuzde = toplam ? Math.round(100 * adet / toplam) : 0;
            el.textContent = `${adet.toLocaleString('tr-TR')} / ${toplam.toLocaleString('tr-TR')} makale (%${yuzde})`;
        };
        kapsamYaz('kapsam-title', counts.title);
        kapsamYaz('kapsam-title-prec', counts.title);
        kapsamYaz('kapsam-abstract', counts.abs);
        kapsamYaz('kapsam-abstract-prec', counts.abs);
        kapsamYaz('kapsam-doi', counts.doi);
        kapsamYaz('kapsam-author', counts.author);
        kapsamYaz('kapsam-author-prec', counts.author);
        kapsamYaz('kapsam-journal', counts.journal);
        kapsamYaz('kapsam-year', counts.year);
        
        // Trigger progress bar animation after a short delay
        setTimeout(() => {
            document.getElementById('title-fill').style.width = `${avgTitle}%`;
            document.getElementById('title-prec-fill').style.width = `${avgTitlePrec}%`;
            document.getElementById('abstract-fill').style.width = `${avgAbs}%`;
            document.getElementById('abstract-prec-fill').style.width = `${avgAbsPrec}%`;
            document.getElementById('doi-fill').style.width = `${avgDoi}%`;
            document.getElementById('author-fill').style.width = `${avgAuthor}%`;
            document.getElementById('author-prec-fill').style.width = `${avgAuthorPrec}%`;
            document.getElementById('journal-fill').style.width = `${avgJournal}%`;
            document.getElementById('year-fill').style.width = `${avgYear}%`;
        }, 500);
    }

    function getScoreClass(score) {
        if(score === null) return 'score-low'; // Will render as gray or low
        if(score >= 70) return 'score-high';
        if(score >= 40) return 'score-med';
        return 'score-low';
    }

    function renderTable() {
        tableBody.innerHTML = '';
        
        const start = (currentPage - 1) * rowsPerPage;
        const end = start + rowsPerPage;
        const paginatedData = currentData.slice(start, end);

        paginatedData.forEach(item => {
            const tr = document.createElement('tr');
            
            const formatScore = (val) => val === null ? "-" : val.toFixed(1) + "%";
            
            const titleScore = item["Başlık Bulma Oranı (%)"];
            const titlePrec = item["Başlık Kesinlik Oranı (%)"];
            const absScore = item["Özet Bulma Oranı (%)"];
            const absPrec = item["Özet Kesinlik Oranı (%)"];
            const authorScore = item["Yazar Bulma Oranı (%)"];
            const authorPrec = item["Yazar Kesinlik Oranı (%)"];
            const keywordScore = item["Kelime Bulma Oranı (%)"];
            const keywordPrec = item["Kelime Kesinlik Oranı (%)"];
            const yearScore = item["Yıl Başarı Oranı (%)"];
            const journalScore = item["Dergi Başarı Oranı (%)"];
            const doiScore = item["DOI Başarı Oranı (%)"];

            tr.innerHTML = `
                <td><strong>${item["Makale ID"]}</strong></td>
                <td><span class="status-badge">${item["Durum"]}</span></td>
                <td><div class="truncate" title="${item["Orijinal Başlık"]}">${item["Orijinal Başlık"] || "-"}</div></td>
                <td><div class="truncate" title="${item["Grobid Başlık"]}">${item["Grobid Başlık"] || "-"}</div></td>
                <td><span class="score-badge ${getScoreClass(titleScore)}">${formatScore(titleScore)} / ${formatScore(titlePrec)}</span></td>
                <td><span class="score-badge ${getScoreClass(absScore)}">${formatScore(absScore)} / ${formatScore(absPrec)}</span></td>
                <td><span class="score-badge ${getScoreClass(authorScore)}">${formatScore(authorScore)} / ${formatScore(authorPrec)}</span></td>
                <td><span class="score-badge ${getScoreClass(keywordScore)}">${formatScore(keywordScore)}</span></td>
                <td><span class="score-badge ${getScoreClass(keywordPrec)}">${formatScore(keywordPrec)}</span></td>
                <td><span class="score-badge ${getScoreClass(doiScore)}">${formatScore(doiScore)}</span></td>
                <td><span class="score-badge ${getScoreClass(journalScore)}">${formatScore(journalScore)}</span></td>
                <td><span class="score-badge ${getScoreClass(yearScore)}">${formatScore(yearScore)}</span></td>
                <td><button class="action-btn view-btn" data-id="${item["Makale ID"]}">İncele</button></td>
            `;
            tableBody.appendChild(tr);
        });

        // Add event listeners to new buttons
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.target.getAttribute('data-id');
                openModal(id);
            });
        });

        updatePagination();
    }

    function updatePagination() {
        const totalPages = Math.ceil(currentData.length / rowsPerPage) || 1;
        pageInfo.textContent = `Sayfa ${currentPage} / ${totalPages}`;
        
        prevBtn.disabled = currentPage === 1;
        nextBtn.disabled = currentPage === totalPages;
    }

    function applyFilters() {
        const search = searchInput.value.toLowerCase();
        const sortVal = sortFilter.value;

        currentData = kiyaslamaVerileri.filter(item => {
            const matchesSearch = 
                String(item["Makale ID"]).toLowerCase().includes(search) ||
                (item["Orijinal Başlık"] || "").toLowerCase().includes(search) ||
                (item["Grobid Başlık"] || "").toLowerCase().includes(search) ||
                (item["Orijinal Anahtar Kelimeler"] || "").toLowerCase().includes(search) ||
                (item["Grobid Anahtar Kelimeler"] || "").toLowerCase().includes(search);
                
            return matchesSearch;
        });

        // Sort
        if(sortVal !== 'default') {
            currentData.sort((a, b) => {
                const aTitle = a["Başlık Başarı Oranı (%)"] || 0;
                const bTitle = b["Başlık Başarı Oranı (%)"] || 0;
                const aAbs = a["Özet Başarı Oranı (%)"] || 0;
                const bAbs = b["Özet Başarı Oranı (%)"] || 0;

                switch(sortVal) {
                    case 'title-desc': return bTitle - aTitle;
                    case 'title-asc': return aTitle - bTitle;
                    case 'abs-desc': return bAbs - aAbs;
                    case 'abs-asc': return aAbs - bAbs;
                }
            });
        }

        currentPage = 1;
        renderTable();
    }

    // Modal functions
    function openModal(id) {
        const item = kiyaslamaVerileri.find(x => String(x["Makale ID"]) === String(id));
        if(!item) return;

        document.getElementById('modal-title').textContent = `Makale Detayları - ${item["Makale ID"]}`;
        modalOrigTitle.textContent = item["Orijinal Başlık"] || "Veri Yok";
        modalOrigAbs.textContent = item["Orijinal Özet"] || "Veri Yok";
        modalOrigAuthors.textContent = item["Orijinal Yazarlar"] || "-";
        modalGrobAuthors.innerHTML = `${item["Grobid Yazarlar"] || "-"}<br><strong style="color:var(--accent);">Bulma Skoru:</strong> ${item["Yazar Bulma Oranı (%)"] === null ? "-" : "%"+item["Yazar Bulma Oranı (%)"].toFixed(1)} | <strong style="color:var(--accent);">Kesinlik (Fazlalık Yok):</strong> ${item["Yazar Kesinlik Oranı (%)"] === null ? "-" : "%"+item["Yazar Kesinlik Oranı (%)"].toFixed(1)}`;
        
        modalOrigKeywords.textContent = item["Orijinal Anahtar Kelimeler"] || "-";
        modalGrobKeywords.innerHTML = `${item["Grobid Anahtar Kelimeler"] || "-"}<br><strong style="color:var(--accent);">Bulma Skoru:</strong> ${item["Kelime Bulma Oranı (%)"] === null ? "-" : "%"+item["Kelime Bulma Oranı (%)"].toFixed(1)} | <strong style="color:var(--accent);">Kesinlik:</strong> ${item["Kelime Kesinlik Oranı (%)"] === null ? "-" : "%"+item["Kelime Kesinlik Oranı (%)"].toFixed(1)}`;
        modalOrigExtra.innerHTML = `<strong>Yıl:</strong> ${item["Orijinal Yıl"] || "-"} | <strong>Dergi:</strong> ${item["Orijinal Dergi"] || "-"} | <strong>DOI:</strong> ${item["Orijinal DOI"] || "-"}`;
        
        modalGrobTitle.textContent = item["Grobid Başlık"] || "Veri Yok";
        modalGrobAbs.textContent = item["Grobid Özet"] || "Veri Yok";
        
        modalGrobExtra.innerHTML = `
            <strong>Yıl:</strong> ${item["Grobid Yıl"] || "-"} <span style="color:var(--accent);">(${item["Yıl Başarı Oranı (%)"] === null ? "-" : "%"+item["Yıl Başarı Oranı (%)"].toFixed(1)})</span> | 
            <strong>Dergi:</strong> ${item["Grobid Dergi"] || "-"} <span style="color:var(--accent);">(${item["Dergi Başarı Oranı (%)"] === null ? "-" : "%"+item["Dergi Başarı Oranı (%)"].toFixed(1)})</span> | 
            <strong>DOI:</strong> ${item["Grobid DOI"] || "-"} <span style="color:var(--accent);">(${item["DOI Başarı Oranı (%)"] === null ? "-" : "%"+item["DOI Başarı Oranı (%)"].toFixed(1)})</span>
        `;

        modal.classList.add('active');
    }

    closeBtn.addEventListener('click', () => {
        modal.classList.remove('active');
    });

    window.addEventListener('click', (e) => {
        if(e.target === modal) {
            modal.classList.remove('active');
        }
    });

    // Event Listeners
    searchInput.addEventListener('input', applyFilters);
    sortFilter.addEventListener('change', applyFilters);
    
    prevBtn.addEventListener('click', () => {
        if(currentPage > 1) {
            currentPage--;
            renderTable();
        }
    });
    
    nextBtn.addEventListener('click', () => {
        const totalPages = Math.ceil(currentData.length / rowsPerPage);
        if(currentPage < totalPages) {
            currentPage++;
            renderTable();
        }
    });

    // Initialize
    initSummaries();
    renderTable();
});
