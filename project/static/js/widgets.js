/**
 * Set date constraints for date input fields
 * Prevents selecting dates in the past or too far in the future (>1 year)
 */
function setDateConstraints(dateInputEl) {
    if (!dateInputEl) {
        console.warn(`Date input element not found`);
        return;
    }
    
    const today = new Date().toISOString().split('T')[0];
    const oneYearFromNow = new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

    dateInputEl.setAttribute('min', today);
    dateInputEl.setAttribute('max', oneYearFromNow);
}