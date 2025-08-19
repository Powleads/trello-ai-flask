# Google Meet AI Analyzer - Workflow PRD

## Overview
This document defines the correct workflow for the Google Meet AI Analyzer to prevent future implementation mistakes.

## User Flow

### Phase 1: Upload & Processing
1. **Upload Section**: User inputs transcript via text/Google Doc/demo
2. **Progress Overlay**: Shows animated progress with 4 steps during AI processing
3. **Upload Form Hidden**: Once processing starts, upload form is completely hidden

### Phase 2: Step 1 - Trello Card Comments  
1. **Card Matching Display**: Shows matched cards with correct confidence percentages (NOT 9000%)
2. **Card Selection**: User can select/deselect cards for comment posting
3. **Actions Available**:
   - **Send to Trello**: Posts AI comments to selected cards → Proceeds to Step 2
   - **Skip Comments**: Skips commenting → Proceeds directly to Step 2

### Phase 3: Step 2 - Meeting Summary Messages
1. **Step 1 Hidden**: Previous step is completely hidden
2. **Summary Display**: Shows group summary and individual assignee messages
3. **Actions Available**:
   - **Send Messages**: Sends WhatsApp messages → Proceeds to completion
   - **Skip Messages**: Skips messaging → Proceeds directly to completion

### Phase 4: Completion
1. **Success Screen**: Shows analysis complete with stats
2. **Start New Analysis**: Button to reload and start over

## Critical Rules

### DO NOT:
- Show percentage confidence over 100% (was showing 9000% due to * 100 bug)
- Let skip buttons stop the workflow entirely 
- Show Step 1 and Step 2 simultaneously
- Show upload form after processing starts
- Skip directly to completion from Step 1

### DO:
- Hide upload form completely when showing results
- Show animated progress overlay during processing
- Ensure skip buttons advance to next step, not end workflow
- Show proper Send/Skip buttons in Step 2
- Extract real attendees and card assignments from API data

## Data Flow

### Real Data Sources:
- **Attendees**: `data.summary.participants` from API response
- **Card Assignments**: Real Trello member assignments mapped via `find_team_member_by_name()`
- **Google Doc URL**: `data.source_url` from API response
- **Card Matches**: `data.matched_cards` with proper confidence scores

### No Demo Data:
- Never use hardcoded "John, Sarah, Mike, Wendy" 
- Always extract real data from backend responses
- Map Trello full names to team member keys properly

## Technical Implementation Notes

### Progress Overlay:
```javascript
showProgressOverlay() // Called when processing starts
hideProgressOverlay() // Called when processing completes/fails
```

### Step Navigation:
```javascript
// Step 1 → Step 2
proceedToSummary() // Hides Step 1, shows Step 2

// Step 2 → Completion  
proceedToCompletion() // Shows final completion screen
sendSummaryMessages() // Sends messages then calls proceedToCompletion()
```

### Form Management:
```javascript
// In showResults()
transcriptForm.style.display = 'none'; // Hide upload form permanently
```

## Backend Endpoints Required:
- `/api/process-transcript` - Main processing
- `/api/demo-analyze` - Demo mode
- `/api/send-summary-messages` - WhatsApp messaging (to be implemented)

## Testing Checklist:
- [ ] Progress overlay shows during processing
- [ ] Upload form hidden after processing starts  
- [ ] Step 1 shows correct confidence percentages
- [ ] Skip button advances to Step 2, not completion
- [ ] Step 2 shows Send/Skip options
- [ ] Real attendee data extracted properly
- [ ] Card assignments use real Trello data
- [ ] Google Doc links included in summaries

---
*Last Updated: Current Session*
*Purpose: Prevent workflow regression and implementation mistakes*