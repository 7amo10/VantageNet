# Alert Management Panel - VANTA-29

## Overview

The Alert Management Panel provides a comprehensive interface for monitoring and managing alerts triggered by emotion detection rules in the VantageNet system.

## Features

### 1. Alert List View

The main alert list displays all triggered alerts with the following information:

- **Severity Level** - Visual badges (Critical, High, Medium, Low) with color coding:
  - 🔴 **Critical**: Red background, highest priority
  - 🟠 **High**: Orange background, high priority
  - 🟡 **Medium**: Yellow background, moderate priority
  - 🟢 **Low**: Green background, informational

- **Rule Name** - The name of the rule that triggered the alert
- **Camera Name** - The camera where the alert was detected
- **Message** - Description of the alert condition
- **Triggered At** - Timestamp when the alert was triggered
- **Status** - Current status (Active, Acknowledged, or Resolved)
- **Actions** - View button to see full details

### 2. Filtering & Search

The interface provides powerful filtering capabilities:

#### Severity Filter
Filter alerts by severity level:
- All (default)
- Low
- Medium
- High
- Critical

#### Status Filter
Filter by acknowledgment status:
- All (default)
- Active - Unacknowledged alerts
- Acknowledged - Alerts that have been acknowledged but not resolved

#### Date Range Filter
Filter alerts by time period:
- **From Date** - Show alerts after this date
- **To Date** - Show alerts before this date

#### Camera Filter
Filter alerts from specific cameras using camera ID

#### Search
Search across alert messages and rule names (case-insensitive)

### 3. Sorting

Click on column headers to sort by:
- Severity level
- Rule name
- Camera name
- Triggered timestamp (default: descending)

Click again to toggle between ascending and descending order.

### 4. Pagination

Navigate through large alert sets:
- Configurable page size (default: 10 items per page)
- Previous/Next page navigation
- Current page indicator

### 5. Alert Details Modal

Click the "View" button on any alert to see full details:

#### Information Displayed
- **Severity Badge** - Visual severity indicator
- **Message** - Full alert message
- **Rule Information**
  - Rule name
  - Rule ID (UUID)
- **Camera Information**
  - Camera name
  - Camera ID (UUID)
- **Timestamp Information**
  - Triggered at (full date/time)
  - Acknowledged at (if applicable)
  - Acknowledged by (username)
- **Status** - Current alert status
- **Additional Metadata** - Any extra contextual data

#### Available Actions

**Acknowledge** (for active alerts only)
- Marks the alert as seen and acknowledged
- Sets acknowledgment timestamp automatically
- Records the user who acknowledged
- Status changes to "Acknowledged"

**Dismiss**
- Soft-deletes the alert (sets resolved_at timestamp)
- Permanently removes from active view
- Confirmation prompt required
- Action is irreversible

**Close**
- Closes the modal without making changes

## API Integration

### Base URL
```
http://localhost:8000/api/alerts/
```

### Endpoints

#### 1. List Alerts
```http
GET /api/alerts/
```

**Query Parameters:**
- `page` (integer, default: 1) - Page number
- `page_size` (integer, default: 50, max: 100) - Items per page
- `severity` (string) - Filter by severity: info, warning, critical
- `status` (string) - Filter by status: active, acknowledged, resolved
- `camera_id` (string) - Filter by camera UUID
- `search` (string) - Search term for message or rule name
- `start_time` (datetime) - Filter alerts after this time
- `end_time` (datetime) - Filter alerts before this time

**Response:**
```json
{
  "alerts": [
    {
      "id": "uuid",
      "rule_id": "uuid",
      "rule_name": "High Anger Detection",
      "camera_id": "uuid",
      "camera_name": "Main Entrance",
      "severity": "high",
      "message": "High anger detected",
      "triggered_at": "2025-01-15T10:30:00Z",
      "acknowledged": false,
      "status": "active"
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 50,
  "total_pages": 2
}
```

#### 2. Get Alert Details
```http
GET /api/alerts/{alert_id}/
```

**Response:**
```json
{
  "id": "uuid",
  "rule_id": "uuid",
  "rule_name": "High Anger Detection",
  "camera_id": "uuid",
  "camera_name": "Main Entrance",
  "severity": "high",
  "message": "High anger detected",
  "triggered_at": "2025-01-15T10:30:00Z",
  "acknowledged": false,
  "acknowledged_at": null,
  "acknowledged_by": null,
  "metadata": {},
  "status": "active"
}
```

#### 3. Update Alert (Acknowledge)
```http
PUT /api/alerts/{alert_id}/
```

**Request Body:**
```json
{
  "acknowledged": true,
  "acknowledged_by": "admin"
}
```

**Response:**
Returns updated alert object with `acknowledged: true` and timestamps.

#### 4. Dismiss Alert
```http
DELETE /api/alerts/{alert_id}/
```

**Response:**
- Status Code: 204 No Content
- Alert is soft-deleted (resolved_at set to current time)

### Error Handling

The API returns standard HTTP status codes:

- `200 OK` - Successful request
- `204 No Content` - Successful deletion
- `400 Bad Request` - Invalid parameters or request body
- `404 Not Found` - Alert not found
- `500 Internal Server Error` - Server-side error

Error responses include details:
```json
{
  "detail": "Error message describing what went wrong"
}
```

## Component Architecture

### AlertsList Component
**Location:** `services/dashboard/src/components/AlertsList.tsx`

**Props:**
- `onAlertSelect?: (alert: Alert) => void` - Callback when alert is clicked

**Functionality:**
- Fetches alerts from API with filters and pagination
- Renders responsive table with alerts
- Provides filter controls
- Handles sorting and pagination
- Shows loading and error states

### AlertDetails Component
**Location:** `services/dashboard/src/components/AlertDetails.tsx`

**Props:**
- `alert: Alert | null` - The alert to display
- `onClose: () => void` - Callback to close the modal
- `onUpdate: () => void` - Callback after acknowledge/dismiss

**Functionality:**
- Displays alert in modal overlay
- Formats timestamps and metadata
- Handles acknowledge and dismiss actions
- Provides confirmation for dismissal
- Shows processing states

### Alerts Page
**Location:** `services/dashboard/src/pages/Alerts.tsx`

**Functionality:**
- Integrates AlertsList and AlertDetails
- Manages selected alert state
- Handles refresh after updates
- Provides page header and description

## Workflow

### Viewing Alerts
1. Navigate to "Alerts" in the navigation menu (🔔 icon)
2. View the alert list with current filters
3. Use filters to narrow down alerts
4. Click column headers to sort
5. Use pagination to navigate through results

### Acknowledging an Alert
1. Click "View" on an alert row
2. Review the alert details in the modal
3. Click "Acknowledge" button
4. Alert status changes to "Acknowledged"
5. Timestamp and user are recorded
6. Modal closes and list refreshes

### Dismissing an Alert
1. Click "View" on an alert row
2. Review the alert details
3. Click "Dismiss" button
4. Confirm the dismissal action
5. Alert is resolved and removed from active view
6. Modal closes and list refreshes

## Troubleshooting

### Alerts Not Loading

**Symptom:** "Failed to fetch" error or empty list

**Solutions:**
1. Check API Gateway is running:
   ```bash
   docker ps | grep vantage-api-gateway
   ```

2. Verify API endpoint is accessible:
   ```bash
   curl http://localhost:8000/api/alerts/
   ```

3. Check browser console for CORS errors
4. Verify database connection in API Gateway logs:
   ```bash
   docker logs vantage-api-gateway
   ```

### Filters Not Working

**Symptom:** Filters don't change the displayed alerts

**Solutions:**
1. Check browser console for JavaScript errors
2. Verify query parameters are being sent (Network tab)
3. Check API Gateway logs for query parsing errors
4. Ensure date filters are in correct format

### Modal Actions Fail

**Symptom:** Acknowledge/Dismiss buttons don't work

**Solutions:**
1. Check browser console for API errors
2. Verify alert ID is valid UUID
3. Check API Gateway logs for backend errors
4. Ensure user has permissions (if auth is enabled)

### CORS Errors

**Symptom:** "CORS policy" errors in browser console

**Solutions:**
1. Verify `config.py` includes your dashboard port:
   ```python
   cors_origins = [
       "http://localhost:3000",
       "http://localhost:3001",
       "http://127.0.0.1:3000",
       "http://127.0.0.1:3001",
   ]
   ```

2. Restart API Gateway after config changes:
   ```bash
   docker compose restart api-gateway
   ```

## Testing

### Manual Testing Checklist

- [ ] Alert list loads successfully
- [ ] Severity filter works for each level
- [ ] Status filter shows correct alerts
- [ ] Date range filter works
- [ ] Search finds alerts by message and rule name
- [ ] Sorting works for each column
- [ ] Pagination Previous/Next buttons work
- [ ] Alert details modal opens
- [ ] Acknowledge button changes status
- [ ] Dismiss button removes alert
- [ ] Close button closes modal
- [ ] List refreshes after actions

### API Testing with curl

**List alerts:**
```bash
curl "http://localhost:8000/api/alerts/?severity=high&page=1"
```

**Get alert details:**
```bash
curl "http://localhost:8000/api/alerts/YOUR_ALERT_ID/"
```

**Acknowledge alert:**
```bash
curl -X PUT "http://localhost:8000/api/alerts/YOUR_ALERT_ID/" \
  -H "Content-Type: application/json" \
  -d '{"acknowledged": true, "acknowledged_by": "test_user"}'
```

**Dismiss alert:**
```bash
curl -X DELETE "http://localhost:8000/api/alerts/YOUR_ALERT_ID/"
```

## Future Enhancements

Potential improvements for future sprints:

1. **Real-time Updates**
   - WebSocket integration for live alert notifications
   - Automatic list refresh when new alerts arrive
   - Browser notifications for critical alerts

2. **Bulk Operations**
   - Select multiple alerts
   - Batch acknowledge
   - Batch dismiss

3. **Export Functionality**
   - CSV export of filtered alerts
   - PDF report generation
   - Email alert summaries

4. **Advanced Analytics**
   - Alert trends over time
   - Heat maps by camera/time
   - Alert response time metrics

5. **User Permissions**
   - Role-based access control
   - Audit log for alert actions
   - Alert assignment to users

## Related Documentation

- [Rule Configuration](./RULES_CONFIGURATION.md) - Managing emotion detection rules
- [API Documentation](../docs/API.md) - Complete API reference
- [Database Schema](../docs/database-schema.md) - Alerts table structure
- [Architecture](../docs/ARCHITECTURE.md) - System architecture overview
