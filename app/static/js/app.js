// Property Lookup Application JavaScript

let currentSearchValue = '';
let currentSearchType = 'number';

document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('searchForm');
    const searchInput = document.getElementById('searchInput');
    const searchLabel = document.getElementById('searchLabel');
    const searchTypeNumber = document.getElementById('searchTypeNumber');
    const searchTypeName = document.getElementById('searchTypeName');
    const searchTypeAddress = document.getElementById('searchTypeAddress');
    const searchBtn = document.getElementById('searchBtn');
    const resultsSection = document.getElementById('resultsSection');
    const noResults = document.getElementById('noResults');
    const errorMessage = document.getElementById('errorMessage');
    const resultsList = document.getElementById('resultsList');
    const resultsCount = document.getElementById('resultsCount');
    const resultsTitle = document.getElementById('resultsTitle');
    const exportCsvBtn = document.getElementById('exportCsvBtn');
    const exportJsonBtn = document.getElementById('exportJsonBtn');
    const reloadBtn = document.getElementById('reloadBtn');
    const suggestionsSection = document.getElementById('suggestionsSection');
    const suggestionsList = document.getElementById('suggestionsList');

    // Update label and placeholder when search type changes
    function updateSearchUI() {
        if (searchTypeNumber.checked) {
            searchLabel.textContent = 'Company Registration Number';
            searchInput.placeholder = 'e.g., 00563409';
            currentSearchType = 'number';
        } else if (searchTypeName.checked) {
            searchLabel.textContent = 'Company Name';
            searchInput.placeholder = 'e.g., AMLG LIMITED';
            currentSearchType = 'name';
        } else if (searchTypeAddress.checked) {
            searchLabel.textContent = 'Property Address or Postcode';
            searchInput.placeholder = 'e.g., 10 Downing Street or SW1A 2AA';
            currentSearchType = 'address';
        }
    }

    searchTypeNumber.addEventListener('change', updateSearchUI);
    searchTypeName.addEventListener('change', updateSearchUI);
    searchTypeAddress.addEventListener('change', updateSearchUI);

    // Search form submission
    searchForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const searchValue = searchInput.value.trim();
        if (!searchValue) {
            showError('Please enter a search value');
            return;
        }

        currentSearchValue = searchValue;
        currentSearchType = searchTypeNumber.checked ? 'number' : (searchTypeName.checked ? 'name' : 'address');
        await performSearch(searchValue, currentSearchType);
    });

    // Export buttons
    exportCsvBtn.addEventListener('click', async function() {
        if (!currentSearchValue) return;
        await exportData('csv');
    });

    exportJsonBtn.addEventListener('click', async function() {
        if (!currentSearchValue) return;
        await exportData('json');
    });

    // Reload data button
    reloadBtn.addEventListener('click', async function() {
        if (!confirm('This will reload all data from the CSV file. This may take several minutes. Continue?')) {
            return;
        }

        reloadBtn.disabled = true;
        reloadBtn.textContent = 'Reloading...';

        try {
            const response = await fetch('/api/reload', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (data.success) {
                alert('Data reloaded successfully!');
            } else {
                alert('Error reloading data: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            alert('Error reloading data: ' + error.message);
        } finally {
            reloadBtn.disabled = false;
            reloadBtn.textContent = 'Reload Data from CSV';
        }
    });

    async function performSearch(searchValue, searchType) {
        // Show loading state
        searchBtn.disabled = true;
        searchBtn.querySelector('.btn-text').style.display = 'none';
        searchBtn.querySelector('.btn-loader').style.display = 'inline-block';
        
        // Hide previous results
        resultsSection.style.display = 'none';
        noResults.style.display = 'none';
        errorMessage.style.display = 'none';
        suggestionsSection.style.display = 'none';

        try {
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    search_type: searchType,
                    search_value: searchValue 
                })
            });

            const data = await response.json();

            if (!data.success) {
                showError(data.error || 'An error occurred');
                return;
            }

            if (data.count === 0) {
                // Check if we have suggestions (only for company name searches)
                if (searchType === 'name' && data.suggestions && data.suggestions.length > 0) {
                    showSuggestions(data.suggestions, searchValue);
                } else {
                    showNoResults();
                }
            } else {
                const searchLabelValue = searchType === 'name' ? data.company_name : (searchType === 'address' ? data.address : data.company_number);
                showResults(data.results, searchLabelValue, data.count, searchType);
            }
        } catch (error) {
            showError('Network error: ' + error.message);
        } finally {
            // Reset loading state
            searchBtn.disabled = false;
            searchBtn.querySelector('.btn-text').style.display = 'inline';
            searchBtn.querySelector('.btn-loader').style.display = 'none';
        }
    }

    function showResults(results, searchLabel, count, searchType) {
        const searchTypeText = searchType === 'name' ? 'Company Name' : (searchType === 'address' ? 'Address' : 'Company Number');
        resultsTitle.textContent = `Properties Found for ${searchTypeText}: ${searchLabel}`;
        resultsCount.textContent = `Found ${count} ${count === 1 ? 'property' : 'properties'}`;
        
        resultsList.innerHTML = results.map(property => `
            <div class="property-card">
                <div class="property-header">
                    <div>
                        <div class="property-title">${escapeHtml(property.property_address || 'N/A')}</div>
                        <div class="property-address">${escapeHtml(property.postcode || '')}</div>
                    </div>
                    ${property.tenure ? `<span class="property-badge">${escapeHtml(property.tenure)}</span>` : ''}
                </div>
                <div class="property-details">
                    ${property.title_number ? `
                        <div class="detail-item">
                            <span class="detail-label">Title Number</span>
                            <span class="detail-value">${escapeHtml(property.title_number)}</span>
                        </div>
                    ` : ''}
                    ${property.district ? `
                        <div class="detail-item">
                            <span class="detail-label">District</span>
                            <span class="detail-value">${escapeHtml(property.district)}</span>
                        </div>
                    ` : ''}
                    ${property.county ? `
                        <div class="detail-item">
                            <span class="detail-label">County</span>
                            <span class="detail-value">${escapeHtml(property.county)}</span>
                        </div>
                    ` : ''}
                    ${property.region ? `
                        <div class="detail-item">
                            <span class="detail-label">Region</span>
                            <span class="detail-value">${escapeHtml(property.region)}</span>
                        </div>
                    ` : ''}
                    ${property.price_paid ? `
                        <div class="detail-item">
                            <span class="detail-label">Price Paid</span>
                            <span class="detail-value">£${formatPrice(property.price_paid)}</span>
                        </div>
                    ` : ''}
                    ${property.proprietor_name ? `
                        <div class="detail-item">
                            <span class="detail-label">Proprietor</span>
                            <span class="detail-value">${escapeHtml(property.proprietor_name)}</span>
                        </div>
                    ` : ''}
                    ${property.company_registration_no ? `
                        <div class="detail-item">
                            <span class="detail-label">Company Number</span>
                            <span class="detail-value">${escapeHtml(property.company_registration_no)}</span>
                        </div>
                    ` : ''}
                    ${property.proprietorship_category ? `
                        <div class="detail-item">
                            <span class="detail-label">Category</span>
                            <span class="detail-value">${escapeHtml(property.proprietorship_category)}</span>
                        </div>
                    ` : ''}
                    ${property.date_proprietor_added ? `
                        <div class="detail-item">
                            <span class="detail-label">Date Added</span>
                            <span class="detail-value">${escapeHtml(property.date_proprietor_added)}</span>
                        </div>
                    ` : ''}
                </div>
            </div>
        `).join('');

        resultsSection.style.display = 'block';
    }

    function showNoResults() {
        const searchTypeText = currentSearchType === 'name' ? 'company name' : (currentSearchType === 'address' ? 'address' : 'company number');
        noResults.innerHTML = `<p>No properties found for this ${searchTypeText}.</p>`;
        noResults.style.display = 'block';
    }

    function showSuggestions(suggestions, originalSearch) {
        noResults.innerHTML = `<p>No properties found for "${escapeHtml(originalSearch)}".</p>`;
        noResults.style.display = 'block';
        
        suggestionsList.innerHTML = suggestions.map(suggestion => `
            <div class="suggestion-item" data-suggestion="${escapeHtml(suggestion.name)}">
                <span class="suggestion-name">${escapeHtml(suggestion.name)}</span>
                <span class="suggestion-similarity">${suggestion.similarity}% match</span>
            </div>
        `).join('');

        // Add click handlers to suggestions
        suggestionsList.querySelectorAll('.suggestion-item').forEach(item => {
            item.addEventListener('click', function() {
                const suggestedName = this.getAttribute('data-suggestion');
                searchInput.value = suggestedName;
                performSearch(suggestedName, 'name');
            });
        });

        suggestionsSection.style.display = 'block';
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.style.display = 'block';
    }

    async function exportData(format) {
        try {
            const endpoint = format === 'csv' ? '/api/export/csv' : '/api/export/json';
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    search_type: currentSearchType,
                    search_value: currentSearchValue 
                })
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || 'Export failed');
            }

            if (format === 'csv') {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                const filename = response.headers.get('Content-Disposition')?.split('filename=')[1]?.replace(/"/g, '') || `properties_${currentSearchValue}.csv`;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            } else {
                const data = await response.json();
                const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                const filename = `properties_${currentSearchType}_${currentSearchValue.replace(/\s+/g, '_')}.json`;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            }
        } catch (error) {
            alert('Export error: ' + error.message);
        }
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function formatPrice(price) {
        if (!price) return 'N/A';
        const num = parseFloat(price);
        if (isNaN(num)) return price;
        return num.toLocaleString('en-GB');
    }
});


