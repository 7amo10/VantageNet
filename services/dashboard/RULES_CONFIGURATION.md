# Rules Configuration UI Documentation

## Overview

The Rules Configuration UI provides a comprehensive interface for creating, managing, and monitoring emotion detection rules in the VantageNet dashboard. It allows users to define custom rules that trigger automated actions based on emotion thresholds, trends, sustained durations, and sentiment analysis.

## Features

### 1. Rule Management
- **Create Rules**: Define new emotion detection rules with custom triggers
- **Edit Rules**: Modify existing rules while preserving their history
- **Delete Rules**: Remove rules with confirmation prompt
- **Enable/Disable**: Toggle rules on/off without deleting them
- **Real-time Status**: See when rules were last triggered

### 2. Rule Types

#### Threshold Rules
Trigger when a specific emotion exceeds a confidence threshold.
- **Use Case**: Alert when anger confidence > 70%
- **Parameters**:
  - Emotion (happy, sad, angry, surprised, neutral, disgusted, fearful)
  - Threshold (0.0 - 1.0)
  - Severity (info, warning, critical)

#### Trend Rules
Detect changes in sentiment over time.
- **Use Case**: Alert when sentiment is declining rapidly
- **Parameters**:
  - Direction (improving / declining)
  - Magnitude threshold (minimum change to trigger)
  - Window size (number of samples to analyze)
  - Severity

#### Duration Rules
Trigger after an emotion persists for a specified time.
- **Use Case**: Alert if someone remains angry for 30+ seconds
- **Parameters**:
  - Emotion
  - Confidence threshold
  - Duration (in seconds)
  - Severity

#### Sentiment Rules
Monitor overall sentiment scores.
- **Use Case**: Alert when overall sentiment drops below threshold
- **Parameters**:
  - Sentiment threshold (0.0 - 1.0)
  - Severity

### 3. Actions

Rules can trigger the following actions when conditions are met:

- **Log**: Record the event in system logs
- **Alert**: Display in-dashboard alert notification
- **Notification**: Send push notification (future)
- **Webhook**: POST event data to external URL (future)
- **Email**: Send email notification (future)

### 4. User Interface Components

#### Rules List View
- **Statistics Dashboard**: Shows total rules, enabled/disabled count, recently triggered
- **Rule Cards**: Display each rule with:
  - Name and enabled/disabled status
  - Rule type and severity badge
  - Action type
  - Human-readable condition description
  - Creation time and last triggered time
  - Quick actions (enable/disable, edit, delete)

#### Rule Form Modal
- **Basic Information**: Name, type selection, action configuration
- **Type-Specific Fields**: Dynamic form based on rule type
- **Visual Sliders**: Easy threshold adjustment with visual feedback
- **Validation**: Real-time form validation with error messages
- **Preview**: Human-readable condition preview

## Usage Guide

### Creating a New Rule

1. Click **"+ New Rule"** button in the top-right
2. Enter a descriptive **Rule Name**
3. Select **Rule Type** (threshold, trend, duration, sentiment)
4. Configure type-specific parameters:
   - For **Threshold**: Select emotion and set threshold slider
   - For **Trend**: Choose direction and magnitude threshold
   - For **Duration**: Select emotion, confidence, and duration
   - For **Sentiment**: Set overall sentiment threshold
5. Choose **Severity** level (info, warning, critical)
6. Select **Action** to trigger (log, alert, etc.)
7. Check **"Enable rule immediately"** if desired
8. Click **"Create Rule"**

### Editing an Existing Rule

1. Locate the rule in the list
2. Click the **edit icon** (pencil) on the right
3. Modify any fields except **Rule Type** (type is locked after creation)
4. Click **"Save Changes"**

### Enabling/Disabling Rules

- Click the **checkmark icon** to toggle rule status
- Enabled rules show green badge and checkmark
- Disabled rules show gray badge and empty circle

### Deleting a Rule

1. Click the **delete icon** (trash) on the right
2. Click **"Confirm"** in the confirmation prompt
3. Or click **"Cancel"** to abort

## API Integration

The Rules Configuration UI integrates with the following API endpoints:

### GET /api/rules
Fetch all rules.

**Response:**
```json
[
  {
    "id": "rule_001",
    "name": "High Anger Detection",
    "type": "threshold",
    "condition_json": {
      "emotion": "angry",
      "threshold": 0.7,
      "severity": "warning"
    },
    "action": "alert",
    "enabled": true,
    "created_at": "2025-12-17T10:00:00Z",
    "updated_at": "2025-12-17T10:00:00Z",
    "last_triggered": "2025-12-17T12:30:00Z"
  }
]
```

### POST /api/rules
Create a new rule.

**Request:**
```json
{
  "name": "Declining Sentiment Alert",
  "type": "trend",
  "condition_json": {
    "direction": "declining",
    "magnitude_threshold": 0.3,
    "window_size": 10,
    "severity": "critical"
  },
  "action": "alert",
  "enabled": true
}
```

### PUT /api/rules/{rule_id}
Update an existing rule.

**Request:**
```json
{
  "enabled": false
}
```
Or full update:
```json
{
  "name": "Updated Rule Name",
  "condition_json": { ... },
  "action": "webhook",
  "enabled": true
}
```

### DELETE /api/rules/{rule_id}
Delete a rule permanently.

## Component Architecture

### RulesConfig Component
**Location**: `src/pages/RulesConfig.tsx`

Main page component that manages:
- Rule fetching from API
- Modal state (open/close, create/edit mode)
- CRUD operations (create, update, delete)
- Enable/disable toggle
- Delete confirmation
- Loading and error states

**State Management:**
- `rules`: Array of Rule objects
- `loading`: Boolean for fetch state
- `error`: Error message string
- `isModalOpen`: Modal visibility
- `selectedRule`: Currently selected rule for editing
- `modalMode`: 'create' or 'edit'
- `deleteConfirm`: Rule ID awaiting delete confirmation

**Key Functions:**
- `fetchRules()`: Load rules from API
- `handleCreateRule()`: POST new rule
- `handleUpdateRule()`: PUT rule updates
- `handleDeleteRule()`: DELETE rule
- `handleToggleEnabled()`: Quick enable/disable toggle
- `formatCondition()`: Convert rule JSON to readable text
- `timeAgo()`: Format timestamps

### RuleFormModal Component
**Location**: `src/components/RuleFormModal.tsx`

Modal dialog for creating and editing rules.

**Props:**
- `isOpen`: Boolean - Modal visibility
- `onClose`: Function - Close handler
- `onSave`: Function - Submit handler (async)
- `rule`: Rule | null - Rule to edit (null for create)
- `mode`: 'create' | 'edit' - Operation mode

**Features:**
- Dynamic form fields based on rule type
- Real-time validation
- Visual sliders for thresholds
- Condition preview text
- Submit/cancel actions
- Loading state during save

**Exports:**
- `RULE_TYPES`: ['threshold', 'trend', 'duration', 'sentiment']
- `RULE_ACTIONS`: ['log', 'alert', 'notification', 'webhook', 'email']
- `EMOTIONS`: ['happy', 'sad', 'angry', 'surprised', 'neutral', 'disgusted', 'fearful']
- `SEVERITIES`: ['info', 'warning', 'critical']
- `TREND_DIRECTIONS`: ['improving', 'declining']

## Styling and Design

### Color Scheme
- **Enabled**: Green badges (`bg-green-100 text-green-800`)
- **Disabled**: Gray badges (`bg-gray-100 text-gray-600`)
- **Severity - Info**: Blue (`bg-blue-100 text-blue-800`)
- **Severity - Warning**: Yellow (`bg-yellow-100 text-yellow-800`)
- **Severity - Critical**: Red (`bg-red-100 text-red-800`)
- **Primary Actions**: Blue buttons (`bg-blue-600`)
- **Delete Actions**: Red buttons/icons (`text-red-600`)

### Responsive Design
- Grid statistics: 1 column on mobile, 4 columns on desktop
- Modal: Max-width 2xl, scrollable on small screens
- Rule cards: Stack on mobile, expand on desktop

### Icons
- **Create**: Plus icon
- **Edit**: Pencil icon
- **Delete**: Trash icon
- **Enable/Disable**: Check circle icon
- **Loading**: Spinning circle

## Error Handling

### API Errors
- Network errors display red alert with retry button
- Individual operation errors show alert() dialog
- Form validation errors highlight fields in red

### Empty States
- No rules: Shows empty state with "Create Rule" CTA
- Disabled rules: Grayed out with disable indicator

### Loading States
- Initial load: Spinning loader with "Loading rules..." text
- Form submit: "Saving..." button text, disabled state
- Optimistic updates: Immediate UI update, rollback on error

## Best Practices

### Rule Naming
- Use descriptive names (e.g., "High Anger Detection" not "Rule 1")
- Include severity level in name if helpful
- Keep names under 200 characters

### Threshold Selection
- Start with moderate thresholds (0.6-0.7)
- Adjust based on false positive/negative rates
- Use "critical" severity sparingly for high-priority alerts

### Action Selection
- Use "log" for debugging and non-critical events
- Use "alert" for in-dashboard notifications
- Reserve "webhook" and "email" for critical alerts (future)

### Rule Organization
- Disable unused rules instead of deleting (preserve history)
- Test new rules in disabled state first
- Review "last triggered" times to identify inactive rules

## Future Enhancements

### Planned Features
1. **Rule Templates**: Pre-configured rules for common scenarios
2. **Bulk Operations**: Enable/disable multiple rules at once
3. **Rule Groups**: Organize rules into categories
4. **Alert History**: View past rule triggers with timestamps
5. **Webhook Configuration**: Test webhooks before saving
6. **Email Notifications**: Configure SMTP and test emails
7. **Rule Analytics**: Track trigger frequency and patterns
8. **Advanced Filtering**: Search and filter rules by type, status, etc.
9. **Rule Copying**: Duplicate existing rules as templates
10. **Import/Export**: Save rules as JSON for backup/sharing

### Advanced Rule Types (Future)
- **Sequence Rules**: Multiple emotions in sequence
- **Composite Rules**: Boolean logic (AND/OR conditions)
- **Time-based Rules**: Active only during specific hours
- **Camera-specific Rules**: Different rules per camera
- **Aggregation Rules**: Group multiple faces/emotions

## Troubleshooting

### Rules Not Loading
- Check API Gateway is running on port 8000
- Verify `/api/rules` endpoint is accessible
- Check browser console for network errors
- Click "Try again" button to retry

### Rule Not Triggering
- Verify rule is **enabled** (green badge)
- Check threshold values are appropriate
- Ensure emotion detection is working
- Review rule condition logic

### Form Validation Errors
- All required fields must be filled
- Thresholds must be between 0.0 and 1.0
- Duration must be positive number
- Window size must be at least 2

### Modal Not Closing
- Click "Cancel" or "×" to close
- Press Escape key (future)
- Ensure no validation errors blocking submit

## Technical Details

### Environment Configuration
```bash
# API Gateway URL (default: http://localhost:8000)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### TypeScript Types
```typescript
interface Rule {
  id: string;
  name: string;
  type: 'threshold' | 'trend' | 'duration' | 'sentiment';
  condition_json: Record<string, any>;
  action: 'log' | 'alert' | 'notification' | 'webhook' | 'email';
  enabled: boolean;
  created_at: string;
  updated_at: string;
  last_triggered?: string;
}
```

### Performance Optimization
- API calls debounced to prevent rapid requests
- Optimistic UI updates for better UX
- Conditional rendering to minimize re-renders
- Lazy loading for large rule lists (future)

## Support

For issues or questions:
1. Check this documentation
2. Review API Gateway logs
3. Inspect browser console for errors
4. Check backend rule engine logs
5. Contact development team

---

**Last Updated**: December 17, 2025
**Version**: 1.0
**Sprint**: 4 - VANTA-28
