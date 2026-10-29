/**
 * AI-Based Smart Baggage Priority & Passenger Assistance System
 * Client-Side JavaScript
 * 
 * Provides interactive modal helpers, AJAX baggage tracking,
 * stepper generation, dynamic badge rendering, and event handlers.
 * All functions are exposed in global scope for template inline onclick handlers.
 */

// ==========================================================================
// 1. Passenger Management Functions
// ==========================================================================

/**
 * Populates and opens the passenger edit modal.
 * @param {string|number} id - Passenger ID or record ID
 * @param {string} name - Passenger full name
 * @param {number} age - Passenger age
 * @param {string} flight - Flight number
 * @param {string} category - Passenger category (e.g. Economy, Business, Elderly, VIP)
 * @param {string} assistance - Special assistance type
 * @param {string} phone - Contact phone number
 */
function editPassenger(id, name, age, flight, category, assistance, phone) {
  const form = document.getElementById('editPassengerForm') || document.querySelector('#editPassengerModal form');
  if (form) {
    form.action = `/passengers/edit/${id}`;
  }

  const setFieldValue = (fieldId, val) => {
    const el = document.getElementById(fieldId);
    if (el) {
      el.value = val !== undefined && val !== null ? val : '';
    }
  };

  setFieldValue('edit_passenger_id', id);
  setFieldValue('edit_name', name);
  setFieldValue('edit_age', age);
  setFieldValue('edit_flight', flight);
  setFieldValue('edit_category', category);
  setFieldValue('edit_assistance', assistance);
  setFieldValue('edit_phone', phone);

  const modalElement = document.getElementById('editPassengerModal');
  if (modalElement && typeof bootstrap !== 'undefined') {
    const modalInstance = bootstrap.Modal.getInstance(modalElement) || new bootstrap.Modal(modalElement);
    modalInstance.show();
  }
}

/**
 * Confirms deletion of a passenger and their dependent baggage/assistance records.
 * @param {string} formId - HTML ID of the form to submit
 */
function confirmDelete(formId) {
  const message = 'Are you sure you want to delete this passenger? This will also delete associated baggage and requests.';
  if (window.confirm(message)) {
    const form = document.getElementById(formId);
    if (form) {
      form.submit();
    } else {
      console.error(`Form with ID "${formId}" not found for deletion.`);
    }
  }
}

// ==========================================================================
// 2. Baggage Status Management
// ==========================================================================

/**
 * Populates and opens the Baggage Status Update Modal.
 * @param {string|number} id - Baggage ID
 * @param {string} currentStatus - Current operational status
 */
function updateStatus(id, currentStatus) {
  const form = document.getElementById('updateStatusForm') || document.querySelector('#updateStatusModal form');
  if (form) {
    form.action = `/baggage/update-status/${id}`;
  }

  const select = document.getElementById('update_status') || 
                 document.getElementById('statusSelect') ||
                 (form ? form.querySelector('select[name="status"]') : null);
  if (select) {
    select.value = currentStatus;
  }

  const idInput = document.getElementById('update_baggage_id');
  if (idInput) {
    idInput.value = id;
  }

  const modalElement = document.getElementById('updateStatusModal');
  if (modalElement && typeof bootstrap !== 'undefined') {
    const modalInstance = bootstrap.Modal.getInstance(modalElement) || new bootstrap.Modal(modalElement);
    modalInstance.show();
  }
}

// ==========================================================================
// 3. Assistance Request Status Management
// ==========================================================================

/**
 * Populates and opens the Assistance Request Update Modal.
 * @param {string|number} id - Assistance Request ID
 * @param {string} currentStatus - Current assistance status
 */
function updateAssistance(id, currentStatus) {
  const form = document.getElementById('updateAssistanceForm') || document.querySelector('#updateAssistanceModal form');
  if (form) {
    form.action = `/assistance/update/${id}`;
  }

  const select = document.getElementById('update_assistance_status') || 
                 document.getElementById('assistanceStatusSelect') ||
                 (form ? form.querySelector('select[name="status"]') : null);
  if (select) {
    select.value = currentStatus;
  }

  const idInput = document.getElementById('update_request_id');
  if (idInput) {
    idInput.value = id;
  }

  const modalElement = document.getElementById('updateAssistanceModal');
  if (modalElement && typeof bootstrap !== 'undefined') {
    const modalInstance = bootstrap.Modal.getInstance(modalElement) || new bootstrap.Modal(modalElement);
    modalInstance.show();
  }
}

// ==========================================================================
// 4. Badge & Visual Utility Functions
// ==========================================================================

/**
 * Returns the Bootstrap badge class for priority level.
 * @param {string} level - 'HIGH', 'MEDIUM', 'LOW'
 * @returns {string} CSS class string
 */
function getBadgeClass(level) {
  const normalized = (level || '').toUpperCase();
  switch (normalized) {
    case 'HIGH':
      return 'bg-danger';
    case 'MEDIUM':
      return 'bg-warning text-dark';
    case 'LOW':
      return 'bg-success';
    default:
      return 'bg-secondary';
  }
}

/**
 * Returns the Bootstrap badge class for a baggage lifecycle status.
 * @param {string} status - Baggage operational status
 * @returns {string} CSS class string
 */
function getStatusBadgeClass(status) {
  const normalized = (status || '').trim();
  switch (normalized) {
    case 'Checked In':
      return 'bg-secondary';
    case 'Processing':
      return 'bg-primary';
    case 'Loaded':
      return 'bg-info text-dark';
    case 'Arrived':
      return 'bg-info text-dark';
    case 'Claim Ready':
      return 'bg-success';
    case 'Collected':
      return 'bg-dark';
    case 'Delayed':
      return 'bg-danger';
    default:
      return 'bg-secondary';
  }
}

/**
 * Formats timestamps into a readable date-time string.
 * @param {string|number|Date} timestamp 
 * @returns {string} Formatted date/time
 */
function formatTime(timestamp) {
  if (!timestamp) return 'N/A';
  try {
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) {
      return String(timestamp);
    }
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });
  } catch (e) {
    return String(timestamp);
  }
}

// ==========================================================================
// 5. Baggage Journey Stepper Generator
// ==========================================================================

/**
 * Generates an interactive multi-step visual indicator for baggage status.
 * Standard sequence: ['Checked In', 'Processing', 'Loaded', 'Arrived', 'Claim Ready', 'Collected']
 * Handles 'Delayed' status specially with red alert markers.
 * 
 * @param {string} status - Current status of baggage
 * @returns {string} Rendered HTML string of the stepper
 */
function buildJourneyStepper(status) {
  const steps = ['Checked In', 'Processing', 'Loaded', 'Arrived', 'Claim Ready', 'Collected'];
  const isDelayed = (status || '').toLowerCase() === 'delayed';
  const currentIndex = steps.findIndex(s => s.toLowerCase() === (status || '').toLowerCase());

  let html = '<div class="journey-stepper">';

  for (let i = 0; i < steps.length; i++) {
    const stepName = steps[i];
    let stepClass = '';
    let icon = i + 1;

    if (isDelayed) {
      if (i === 1) { // flag delay at processing/transit stage
        stepClass = 'delayed';
        icon = '<i class="fa-solid fa-triangle-exclamation"></i>';
      } else if (i < 1) {
        stepClass = 'completed';
        icon = '<i class="fa-solid fa-check"></i>';
      }
    } else if (currentIndex >= 0) {
      if (i < currentIndex) {
        stepClass = 'completed';
        icon = '<i class="fa-solid fa-check"></i>';
      } else if (i === currentIndex) {
        stepClass = 'current';
        icon = '<i class="fa-solid fa-plane-departure"></i>';
      }
    }

    html += `
      <div class="journey-step ${stepClass}">
        <div class="step-circle">${icon}</div>
        <div class="step-label">${stepName}</div>
      </div>
    `;

    // Connector line between steps (except after the last step)
    if (i < steps.length - 1) {
      const connectorCompleted = !isDelayed && currentIndex > i ? 'completed' : '';
      html += `<div class="journey-connector ${connectorCompleted}"></div>`;
    }
  }

  html += '</div>';
  return html;
}

// ==========================================================================
// 6. Live Baggage & Passenger Tracking API Integration
// ==========================================================================

/**
 * Performs AJAX search for baggage tag or passenger ID.
 */
function trackBaggage() {
  const input = document.getElementById('trackingQuery');
  if (!input) {
    console.error('Tracking query input element (#trackingQuery) not found.');
    return;
  }

  const query = input.value.trim();
  const resultsContainer = document.getElementById('trackingResults');
  const errorContainer = document.getElementById('trackingError');

  if (errorContainer) {
    errorContainer.classList.add('d-none');
    errorContainer.innerHTML = '';
  }

  if (!query) {
    if (errorContainer) {
      errorContainer.innerHTML = `
        <div class="alert alert-warning d-flex align-items-center" role="alert">
          <i class="fa-solid fa-circle-exclamation me-2"></i>
          <div>Please enter a valid Baggage Tag ID or Passenger ID to track.</div>
        </div>
      `;
      errorContainer.classList.remove('d-none');
    } else {
      alert('Please enter a valid Baggage Tag ID or Passenger ID.');
    }
    input.focus();
    return;
  }

  // Show loading indicator
  if (resultsContainer) {
    resultsContainer.classList.remove('d-none');
    resultsContainer.innerHTML = `
      <div class="text-center py-5">
        <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
          <span class="visually-hidden">Loading...</span>
        </div>
        <p class="mt-3 text-muted fw-semibold">Searching airport baggage records for "${escapeHtml(query)}"...</p>
      </div>
    `;
  }

  // Execute API Request
  fetch(`/api/track?query=${encodeURIComponent(query)}`)
    .then(response => {
      if (!response.ok) {
        return response.json().then(errData => {
          throw new Error(errData.error || `Error: Received response code ${response.status}`);
        });
      }
      return response.json();
    })
    .then(data => {
      if (data.error) {
        throw new Error(data.error);
      }
      displayTrackingResults(data);
    })
    .catch(err => {
      console.warn('Tracking query failed:', err.message);
      if (resultsContainer) {
        resultsContainer.innerHTML = `
          <div class="card shadow-sm border-0 mt-3">
            <div class="card-body text-center py-5">
              <i class="fa-solid fa-circle-exclamation text-warning mb-3" style="font-size: 3rem;"></i>
              <h5 class="fw-bold text-dark">No Tracking Record Found</h5>
              <p class="text-secondary mb-4">${escapeHtml(err.message || 'No matching baggage or passenger found with the identifier provided.')}</p>
              <div class="small text-muted">
                Tip: Verify the tag format (e.g. <code>BAG101</code>) or passenger identifier.
              </div>
            </div>
          </div>
        `;
      }
    });
}

/**
 * Escapes HTML characters to prevent XSS.
 * @param {string} str 
 * @returns {string} Safe string
 */
function escapeHtml(str) {
  if (str === undefined || str === null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/**
 * Renders passenger, baggage, and assistance data onto the tracking page.
 * @param {Object} data - Payload matching API response specification
 */
function displayTrackingResults(data) {
  const container = document.getElementById('trackingResults');
  if (!container) return;

  const passenger = data.passenger || {};
  const baggageList = Array.isArray(data.baggage) ? data.baggage : (data.baggage ? [data.baggage] : []);
  const assistanceList = Array.isArray(data.assistance_requests) ? data.assistance_requests : [];

  let html = `
    <!-- Top Row: Passenger Details & Baggage Summary -->
    <div class="row g-4 mb-4">
      <!-- Passenger Card -->
      <div class="col-lg-5">
        <div class="card h-100 shadow-sm border-0">
          <div class="card-header bg-primary text-white d-flex align-items-center">
            <i class="fa-solid fa-user me-2"></i>
            <h5 class="mb-0">Passenger Information</h5>
          </div>
          <div class="card-body">
            <div class="d-flex align-items-center mb-3">
              <div class="rounded-circle bg-light d-flex align-items-center justify-content-center me-3" style="width: 52px; height: 52px; font-size: 1.5rem; color: #1a237e;">
                <i class="fa-solid fa-id-card"></i>
              </div>
              <div>
                <h4 class="fw-bold mb-0 text-primary">${escapeHtml(passenger.name || 'Unknown Passenger')}</h4>
                <span class="badge bg-secondary">ID: ${escapeHtml(passenger.passenger_id || 'N/A')}</span>
                <span class="badge bg-info text-dark ms-1">${escapeHtml(passenger.category || 'Standard')}</span>
              </div>
            </div>
            <hr class="my-3">
            <div class="row g-2">
              <div class="col-6">
                <span class="text-secondary small d-block">Flight Number</span>
                <strong class="text-dark"><i class="fa-solid fa-plane-up me-1 text-primary"></i> ${escapeHtml(passenger.flight_number || 'N/A')}</strong>
              </div>
              <div class="col-6">
                <span class="text-secondary small d-block">Passenger Age</span>
                <strong class="text-dark"><i class="fa-solid fa-cake-candles me-1 text-secondary"></i> ${escapeHtml(passenger.age ? passenger.age + ' yrs' : 'N/A')}</strong>
              </div>
              <div class="col-6 mt-3">
                <span class="text-secondary small d-block">Phone Contact</span>
                <strong class="text-dark"><i class="fa-solid fa-phone me-1 text-success"></i> ${escapeHtml(passenger.phone || 'N/A')}</strong>
              </div>
              <div class="col-6 mt-3">
                <span class="text-secondary small d-block">Total Checked Bags</span>
                <strong class="text-dark"><i class="fa-solid fa-suitcase-rolling me-1 text-warning"></i> ${baggageList.length}</strong>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Assistance Requests Preview -->
      <div class="col-lg-7">
        <div class="card h-100 shadow-sm border-0">
          <div class="card-header bg-primary text-white d-flex align-items-center justify-content-between">
            <div class="d-flex align-items-center">
              <i class="fa-solid fa-wheelchair me-2"></i>
              <h5 class="mb-0">Assistance Requests</h5>
            </div>
            <span class="badge bg-light text-dark">${assistanceList.length} Request(s)</span>
          </div>
          <div class="card-body p-0">
  `;

  if (assistanceList.length === 0) {
    html += `
      <div class="p-4 text-center text-muted">
        <i class="fa-regular fa-circle-check fs-2 text-success mb-2"></i>
        <p class="mb-0">No special assistance requested for this passenger.</p>
      </div>
    `;
  } else {
    html += `<ul class="list-group list-group-flush">`;
    assistanceList.forEach(req => {
      let statusBadge = 'bg-secondary';
      if (req.status === 'Completed') statusBadge = 'bg-success';
      else if (req.status === 'In Progress' || req.status === 'Assigned') statusBadge = 'bg-primary';
      else if (req.status === 'Pending') statusBadge = 'bg-warning text-dark';

      html += `
        <li class="list-group-item d-flex justify-content-between align-items-center py-3 px-4">
          <div class="d-flex align-items-center">
            <div class="notif-icon me-3 bg-light rounded-circle p-2 text-primary" style="width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;">
              <i class="fa-solid fa-hand-holding-heart"></i>
            </div>
            <div>
              <strong class="d-block text-dark">${escapeHtml(req.assistance_type || 'Special Assistance')}</strong>
              <small class="text-muted">Request #${escapeHtml(req.request_id)}</small>
            </div>
          </div>
          <span class="badge ${statusBadge}">${escapeHtml(req.status || 'Pending')}</span>
        </li>
      `;
    });
    html += `</ul>`;
  }

  html += `
          </div>
        </div>
      </div>
    </div>
  `;

  // Baggage Items and Steppers Section
  if (baggageList.length === 0) {
    html += `
      <div class="alert alert-info">
        <i class="fa-solid fa-circle-info me-2"></i> No checked luggage associated with this passenger record.
      </div>
    `;
  } else {
    baggageList.forEach((bag, idx) => {
      const priorityBadgeClass = getBadgeClass(bag.priority_level);
      const statusBadgeClass = getStatusBadgeClass(bag.status);
      const score = Math.round(Number(bag.priority_score) || 0);

      let fillClass = 'low';
      if (score >= 70) fillClass = 'high';
      else if (score >= 40) fillClass = 'medium';

      html += `
        <div class="card shadow-sm border-0 mb-4">
          <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center flex-wrap gap-2">
            <div class="d-flex align-items-center gap-2">
              <i class="fa-solid fa-suitcase-rolling"></i>
              <h5 class="mb-0">Baggage Tag: ${escapeHtml(bag.baggage_id)}</h5>
            </div>
            <div class="d-flex align-items-center gap-2">
              <span class="badge ${priorityBadgeClass} px-3 py-2">
                <i class="fa-solid fa-bolt me-1"></i> Priority: ${escapeHtml(bag.priority_level || 'NORMAL')}
              </span>
              <span class="badge ${statusBadgeClass} px-3 py-2">
                ${escapeHtml(bag.status || 'Checked In')}
              </span>
            </div>
          </div>

          <div class="card-body p-4">
            <!-- Journey Stepper -->
            <div class="mb-4">
              <h6 class="text-secondary fw-bold text-uppercase small mb-2">Live Journey Stage</h6>
              ${buildJourneyStepper(bag.status)}
            </div>

            <!-- Priority & Delay Risk Metrics -->
            <div class="row g-3 bg-light rounded-3 p-3">
              <div class="col-md-3">
                <span class="text-secondary small d-block">Priority Score</span>
                <div class="d-flex align-items-center gap-2 mt-1">
                  <div class="priority-bar flex-grow-1" style="height: 10px;">
                    <div class="fill ${fillClass}" style="width: ${Math.min(100, Math.max(0, score))}%;"></div>
                  </div>
                  <strong class="text-dark">${score}/100</strong>
                </div>
              </div>

              <div class="col-md-3">
                <span class="text-secondary small d-block">Estimated Wait / Handling Time</span>
                <strong class="text-dark fs-6">
                  <i class="fa-regular fa-clock me-1 text-primary"></i>
                  ${escapeHtml(bag.estimated_wait || '15 mins')}
                </strong>
              </div>

              <div class="col-md-3">
                <span class="text-secondary small d-block">Delay Risk Assessment</span>
                <strong class="${(bag.delay_risk || '').toLowerCase() === 'high' ? 'text-danger' : 'text-success'} fs-6">
                  <i class="fa-solid fa-triangle-exclamation me-1"></i>
                  ${escapeHtml(bag.delay_risk || 'Normal')}
                </strong>
              </div>

              <div class="col-md-3">
                <span class="text-secondary small d-block">Delay Reason / Note</span>
                <span class="text-dark small">${escapeHtml(bag.delay_reason || 'On schedule')}</span>
              </div>

              ${bag.priority_reason ? `
                <div class="col-12 mt-2 pt-2 border-top">
                  <span class="text-secondary small d-block">Priority Determination Basis</span>
                  <p class="mb-0 small text-dark"><i class="fa-solid fa-calculator me-1 text-primary"></i> ${escapeHtml(bag.priority_reason)}</p>
                </div>
              ` : ''}
            </div>
          </div>
        </div>
      `;
    });
  }

  container.innerHTML = html;
  container.classList.remove('d-none');
}

// ==========================================================================
// 7. Event Listeners & Initialization
// ==========================================================================

document.addEventListener('DOMContentLoaded', function () {
  // 1. Hook tracking button if present
  const trackBtn = document.getElementById('trackButton') || document.getElementById('btnTrackBaggage');
  if (trackBtn) {
    trackBtn.addEventListener('click', function (e) {
      e.preventDefault();
      trackBaggage();
    });
  }

  // 2. Hook tracking input for Enter key
  const trackInput = document.getElementById('trackingQuery');
  if (trackInput) {
    trackInput.addEventListener('keypress', function (e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        trackBaggage();
      }
    });

    // Auto-search if query parameter exists in URL (?query=BAG101)
    const urlParams = new URLSearchParams(window.location.search);
    const qParam = urlParams.get('query') || urlParams.get('q');
    if (qParam) {
      trackInput.value = qParam;
      trackBaggage();
    }
  }

  // 3. Mobile sidebar toggle button
  const sidebarToggle = document.getElementById('sidebarToggle') || document.querySelector('.sidebar-toggle-btn');
  const sidebar = document.querySelector('.sidebar');
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', function () {
      sidebar.classList.toggle('show');
    });
  }

  // 4. Close mobile sidebar when clicking outside
  document.addEventListener('click', function (e) {
    if (sidebar && sidebar.classList.contains('show')) {
      if (!sidebar.contains(e.target) && (!sidebarToggle || !sidebarToggle.contains(e.target))) {
        sidebar.classList.remove('show');
      }
    }
  });

  // 5. Auto dismiss flash alerts after 5 seconds
  const autoAlerts = document.querySelectorAll('.alert-dismissible');
  autoAlerts.forEach(alert => {
    setTimeout(() => {
      try {
        if (typeof bootstrap !== 'undefined' && bootstrap.Alert) {
          const bsAlert = new bootstrap.Alert(alert);
          bsAlert.close();
        }
      } catch (err) {
        // Fallback fade out
        alert.style.transition = 'opacity 0.5s ease';
        alert.style.opacity = '0';
        setTimeout(() => alert.remove(), 500);
      }
    }, 5000);
  });
});

// Explicitly assign all functions to window to guarantee template onclick availability
window.editPassenger = editPassenger;
window.confirmDelete = confirmDelete;
window.updateStatus = updateStatus;
window.updateAssistance = updateAssistance;
window.trackBaggage = trackBaggage;
window.displayTrackingResults = displayTrackingResults;
window.buildJourneyStepper = buildJourneyStepper;
window.getBadgeClass = getBadgeClass;
window.getStatusBadgeClass = getStatusBadgeClass;
window.formatTime = formatTime;
