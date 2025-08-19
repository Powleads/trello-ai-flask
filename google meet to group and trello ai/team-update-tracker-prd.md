# Team Update Tracker - Product Requirements Document

## Executive Summary
A comprehensive team productivity monitoring application that tracks Trello card assignments, monitors comment activity, and automatically sends update requests via WhatsApp using Green API integration. The system provides analytics on team performance and automates follow-up processes.

## Product Vision
Create an intelligent team management system that proactively identifies tasks lacking updates, automates communication with team members, and provides insights into team productivity patterns.

## Core Features

### 1. Multi-App Architecture
- **Top Navigation Menu**: Clean, modern menu bar allowing easy switching between apps
- **Modular Design**: Extensible architecture for adding future applications
- **Current Apps**: 
  - Google Meet to Group Trello AI (existing)
  - Team Update Tracker (new)

### 2. Card Scanning & Assignment Detection
- **Automatic Scanning**: Scan all Trello cards to identify assigned team members
- **Comment Analysis**: Monitor comments for updates within the last 24 hours
- **Assignment Tracking**: Track which cards have no assigned members

### 3. Update Request System
- **Visual Dashboard**: Display cards needing updates with clear highlighting
- **Assignee Information**: Show assigned person and time since last comment
- **Bulk Selection**: Allow users to select multiple cards for bulk actions
- **WhatsApp Integration**: Send update requests via Green API

### 4. Automated Scheduling
- **Weekday Automation**: Schedule automatic checks Monday-Friday
- **Customizable Time**: User-configurable execution time
- **Smart Notifications**: Only send notifications when updates are needed

### 5. Escalation Management
- **Request Counter**: Track number of update requests sent per card/user
- **Three-Strike Rule**: After 3 unanswered requests, escalate to group
- **Group Notifications**: Alert main group about persistent non-responders

### 6. Analytics Dashboard
- **Card Movement Tracking**: Monitor progression from "New Task" to "Complete"
- **Performance Metrics**: Time taken for task completion
- **Team Performance**: Identify users with poor commenting habits
- **Productivity Insights**: Visual charts and statistics

## Technical Specifications

### Green API Integration
**Connection Details** (Extracted from blueprint):
- **Instance ID**: 7105263120
- **Group Chat**: 447916991875@c.us

**Team Member Phone Numbers**:
- Criselle: 639494048499@c.us
- Lancey: 639264438378@c.us
- Ezechiel: 23754071907@c.us
- Levy: 237659250977@c.us
- Wendy: 237677079267@c.us
- Forka: 237652275097@c.us
- Breyden: 13179979692@c.us
- Brayan: 237676267420@c.us

### Data Structure
```javascript
{
  cards: [
    {
      id: "string",
      name: "string",
      url: "string",
      assignedMembers: ["string"],
      lastCommentDate: "datetime",
      updateRequestCount: number,
      stage: "string",
      createdDate: "datetime",
      completedDate: "datetime"
    }
  ],
  teamMembers: [
    {
      name: "string",
      phoneNumber: "string",
      responseRate: number,
      avgResponseTime: number
    }
  ]
}
```

## User Interface Design

### Layout Structure
```
┌─────────────────────────────────────────────────────────┐
│ 🏠 Home | 📹 Google Meet | 📊 Update Tracker | ➕ More   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 📋 CARDS NEEDING UPDATES                               │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ☑️ Task Name | 👤 Assignee | ⏰ 2 days ago          │ │
│ │ ☑️ Another Task | 👤 User B | ⏰ 3 days ago         │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ [📱 Send WhatsApp Updates] [⚙️ Settings] [📅 Schedule]   │
│                                                         │
│ 📊 ANALYTICS DASHBOARD                                 │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 📈 Card Movement | 👥 Team Performance | 📅 Trends  │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Modern UI Elements
- **Color Scheme**: Clean white background with blue accents (#2563eb)
- **Typography**: Inter font family for readability
- **Icons**: Lucide React icons for consistency
- **Components**: Shadcn/ui for modern, accessible components
- **Responsive**: Mobile-first design approach

## User Stories

### Primary User Stories
1. **As a project manager**, I want to see which team members haven't provided updates so I can follow up appropriately
2. **As a team lead**, I want to automatically send reminder messages to team members who haven't commented on their assigned tasks
3. **As an administrator**, I want to track team performance metrics to identify improvement areas
4. **As a user**, I want to schedule automatic checks so I don't have to manually monitor tasks daily

### Secondary User Stories
1. **As a team member**, I want to receive clear, actionable WhatsApp messages about my pending tasks
2. **As a manager**, I want to be notified when team members consistently don't respond to update requests
3. **As an analyst**, I want to see historical data about task completion times and team efficiency

## Message Templates

### Individual Update Request
```
Hello [Name], This is the JGV EEsystems AI Trello bot

Here are the tasks today that you are assigned to and have not had a comment recently:

[Task List with URLs]

Please click the links to open Trello and write a comment. If there is an issue, please contact James in the EEsystems group chat.

Thanks
```

### Group Escalation Message
```
⚠️ URGENT: Unassigned Tasks Requiring Attention

The following cards need to be assigned immediately:
[List of unassigned task URLs]

Please assign these tasks as soon as possible.
```

### Persistent Non-Response Alert
```
🚨 ESCALATION NOTICE

[Team Member Name] has not responded to 3 update requests for the following tasks:
[Task URLs]

Immediate action required for task completion.
```

## Implementation Phases

### Phase 1: Core Functionality (Week 1-2)
- Multi-app navigation setup
- Trello API integration for card scanning
- Basic UI for displaying cards needing updates
- Green API integration for WhatsApp messaging

### Phase 2: Automation & Scheduling (Week 3)
- Automated scheduling system
- Request tracking and counting
- Escalation logic implementation

### Phase 3: Analytics & Reporting (Week 4)
- Analytics dashboard development with comprehensive metrics
- Performance metrics calculation and trending
- Historical data tracking and pattern analysis
- Visual charts and interactive reports
- Real-time team productivity insights

### Phase 4: Enhancement & Polish (Week 5)
- UI/UX improvements
- Performance optimization
- Error handling and edge cases
- Testing and bug fixes

## Technical Architecture

### Frontend
- **Framework**: React with TypeScript
- **Styling**: Tailwind CSS + Shadcn/ui
- **State Management**: Zustand or Context API
- **API Client**: Axios for HTTP requests

### Backend/Integration
- **Trello API**: Card and comment data retrieval
- **Green API**: WhatsApp message sending
- **Storage**: Local storage/SQLite for tracking data
- **Scheduling**: Node-cron for automated tasks

### Data Flow
1. Scan Trello boards for cards and assignments
2. Analyze comment timestamps
3. Identify cards needing updates
4. Display in UI with selection capabilities
5. Send WhatsApp messages via Green API
6. Track responses and update counters
7. Generate analytics and reports

## Success Metrics
- **Response Rate**: Increase in team member comment frequency
- **Task Completion Time**: Reduction in average task completion duration
- **Update Compliance**: Percentage of tasks with recent updates
- **User Adoption**: Active usage of the application by team leads

## Future Enhancements
- Integration with other project management tools (Asana, Monday.com)
- Email notification fallback option
- Advanced analytics with ML-powered insights
- Mobile app version
- Slack integration
- Custom notification templates
- Team performance scoring system

## Risk Mitigation
- **API Rate Limits**: Implement request throttling and caching
- **WhatsApp Blocks**: Respect messaging frequency limits
- **Data Privacy**: Ensure secure handling of team member information
- **System Reliability**: Implement error handling and retry mechanisms

## Detailed Analytics Requirements

### Core Analytics Features

#### 1. Team Performance Metrics Dashboard
- **Individual Performance Tracking**
  - Response rate to update requests (%)
  - Average response time to messages (hours)
  - Task completion velocity (tasks/week)
  - Comment frequency and quality scores
  - Productivity trends over time (daily/weekly/monthly)

- **Team Comparison Views**
  - Side-by-side performance comparisons
  - Ranking system with gamification elements
  - Performance improvement tracking
  - Team collaboration effectiveness scores

#### 2. Card Movement Analytics
- **Task Lifecycle Tracking**
  - Time spent in each Trello list/stage
  - Average time from assignment to completion
  - Bottleneck identification in workflow
  - Card movement velocity tracking
  - Completion rate trends

- **Project Progress Visualization**
  - Kanban flow efficiency metrics
  - Work-in-progress (WIP) limits analysis
  - Cycle time and lead time measurements
  - Throughput analysis (cards completed per sprint/week)

#### 3. Communication Analytics
- **Message Effectiveness Tracking**
  - Open rates for WhatsApp messages
  - Response rates by message type
  - Optimal sending time analysis
  - Message frequency impact on productivity
  - Escalation trigger effectiveness

- **Update Quality Assessment**
  - Comment length and detail analysis
  - Update frequency patterns
  - Proactive vs reactive communication ratios
  - Quality score based on AI sentiment analysis

#### 4. Predictive Analytics & Insights
- **Risk Prediction**
  - Cards at risk of missing deadlines
  - Team members likely to need additional support
  - Project bottleneck early warning system
  - Workload balance predictions

- **Optimization Recommendations**
  - Best practices suggestions based on high performers
  - Workflow optimization opportunities
  - Resource allocation recommendations
  - Communication strategy improvements

### Visual Components

#### 1. Interactive Charts & Graphs
- **Performance Trends**: Line charts showing individual and team performance over time
- **Task Distribution**: Pie charts showing workload distribution across team members
- **Completion Rates**: Bar charts comparing completion rates by person/project/time period
- **Response Time Heatmaps**: Visual representation of response patterns throughout the day/week

#### 2. Real-time Dashboards
- **Executive Summary View**: High-level KPIs for management
- **Team Lead Dashboard**: Detailed team performance and intervention opportunities
- **Individual Performance**: Personal productivity tracking for team members
- **Project Health Monitor**: Overall project status and risk indicators

#### 3. Drill-down Capabilities
- **Click-through Analysis**: Ability to drill down from overview to specific details
- **Time Range Selection**: Flexible date range filtering (last 7 days, month, quarter)
- **Filter Options**: By team member, project, card type, priority level
- **Export Functionality**: CSV/PDF export for reporting and external analysis

### Data Collection & Storage

#### 1. Metrics Captured
- **User Actions**: Button clicks, page views, interaction patterns
- **Response Patterns**: Message read receipts, response times, engagement levels
- **Card Metadata**: Creation date, assignment date, completion date, comment history
- **System Performance**: API response times, error rates, processing delays

#### 2. Data Warehouse Design
- **Time-series Database**: For tracking metrics over time
- **User Behavior Tracking**: Interaction patterns and usage analytics
- **Performance Benchmarking**: Historical data for trend analysis
- **Data Retention Policy**: Configurable retention periods for different data types

### Implementation Priority

#### Phase 3A: Core Analytics (Week 4.1-4.3)
1. **Basic Performance Metrics**
   - Response rate tracking
   - Task completion monitoring
   - Simple trend visualization

2. **Team Comparison Dashboard**
   - Individual performance cards
   - Basic ranking system
   - Performance trend graphs

#### Phase 3B: Advanced Analytics (Week 4.4-4.5)
1. **Predictive Features**
   - Risk identification algorithms
   - Performance prediction models
   - Bottleneck detection system

2. **Interactive Visualizations**
   - Drill-down capabilities
   - Real-time data updates
   - Advanced filtering options

### Success Metrics for Analytics
- **User Adoption**: 80% of team leads actively use analytics dashboard weekly
- **Insight Actionability**: 90% of recommendations lead to measurable improvements
- **Performance Improvement**: 25% increase in team response rates within first month
- **Time Savings**: 3+ hours per week saved in manual performance tracking

### Technical Implementation
- **Frontend**: Chart.js or D3.js for interactive visualizations
- **Backend**: Time-series database (InfluxDB) for metrics storage
- **Real-time Updates**: WebSocket connections for live dashboard updates
- **Data Processing**: Background jobs for metric calculations and trend analysis

This comprehensive analytics system will transform the team tracker from a simple monitoring tool into a powerful productivity optimization platform that provides actionable insights for continuous improvement.

---

This PRD provides a comprehensive foundation for building a powerful team update tracking system that automates communication, provides valuable insights, and helps maintain team productivity.