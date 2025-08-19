#!/usr/bin/env python3
"""
Test Data for Google Meet Processing - Assignment Detection Validation
"""

# Sample meeting transcripts for testing assignment detection
SAMPLE_TRANSCRIPTS = {
    "explicit_assignment": """
Admin: Good morning everyone. Let's discuss the mobile app progress.
Wendy: I've been working on the user interface design.
Admin: Great. Wendy, can you handle the mobile app login feature?
Wendy: Sure, I'll take care of that.
Lancey: What about the website updates?
Admin: Lancey, please work on the landing page optimization.
Levy: I can help with the backend API integration.
Admin: Perfect. Let's also discuss the WordPress site improvements.
""",
    
    "checklist_assignment": """
Sarah: Let's review the project assignments from our checklist.
Admin: For the mobile app, we have Wendy assigned to the UI components.
Mike: The checklist shows Lancey responsible for the website redesign.
Admin: And Levy is handling the API documentation.
Emily: What about the task management system?
Admin: That's still unassigned in the checklist.
""",
    
    "multiple_assignments": """
Project Manager: We need to discuss the e-commerce project.
Admin: Both Wendy and Lancey will work on the mobile app together.
Wendy: I'll handle the frontend components.
Lancey: And I'll manage the backend integration.
Admin: For the website updates, we'll have Levy and Ezechiel collaborate.
Levy: I'll focus on the design aspects.
Ezechiel: I'll handle the technical implementation.
""",
    
    "admin_filtering": """
Admin: Let's start the meeting about our current projects.
Criselle: I've been reviewing the mobile app requirements.
Admin: Criselle, can you update the mobile app specifications?
Criselle: Sure, I'll handle that documentation.
Wendy: What about the actual development work?
Admin: Wendy, you'll be responsible for the mobile app development.
Wendy: Perfect, I'll start working on it tomorrow.
Admin: Criselle will coordinate with the client.
""",
    
    "default_assignment_mobile": """
Team Lead: We have a new mobile application project.
Developer: The mobile app needs iOS and Android support.
Manager: This is for the new smartphone application.
Team Lead: We need someone to handle the app development.
Developer: The mobile platform requirements are complex.
Manager: Let's move forward with the app architecture.
""",
    
    "default_assignment_web": """
Project Manager: We have a new website project.
Designer: The website needs modern responsive design.
Developer: We need WordPress integration for the site.
Project Manager: The landing page is a priority.
Designer: The frontend needs to be mobile-friendly.
Developer: We'll use HTML5 and CSS3 for the website.
""",
    
    "no_clear_assignment": """
Team Lead: Let's discuss general project updates.
Manager: How are things progressing overall?
Developer: We've made good progress on various tasks.
Designer: The design phase is moving along well.
Team Lead: Great to hear everyone is busy.
Manager: Keep up the good work team.
""",
    
    "complex_conversation": """
Admin: Good morning team. Let's review our current Trello cards.
Wendy: I see the mobile app card needs some attention.
Admin: Yes, Wendy, can you take the lead on the mobile app development?
Wendy: Absolutely, I'll handle the entire mobile application.
Lancey: What about the website redesign card?
Admin: Lancey, please work on the website improvements.
Lancey: Got it, I'll focus on the landing page optimization.
Levy: I noticed the API documentation card is still pending.
Admin: Levy, can you handle the API documentation and integration?
Levy: Sure thing, I'll take care of the API work.
Criselle: I'll coordinate with clients for requirements.
Admin: Thanks Criselle, but Wendy will be the main contact for mobile app clients.
Ezechiel: Should I help with any backend work?
Admin: Ezechiel, you can assist Levy with the API backend tasks.
"""
}

# Mock Trello card data for testing
MOCK_TRELLO_CARDS = [
    {
        "id": "card_mobile_app_123",
        "name": "Mobile App Development",
        "description": "Develop iOS and Android mobile application",
        "checklists": [
            {
                "name": "Team Assignments",
                "checkItems": [
                    {"name": "@wendy - UI Development"},
                    {"name": "@lancey - Backend API"},
                    {"name": "Testing - TBD"}
                ]
            }
        ],
        "recent_comments": [
            {"memberCreator": {"fullName": "Wendy Johnson"}, "date": "2025-08-18T10:00:00Z", "text": "Started working on login screen"},
            {"memberCreator": {"fullName": "Admin User"}, "date": "2025-08-18T09:00:00Z", "text": "Please prioritize this task"}
        ]
    },
    
    {
        "id": "card_website_456", 
        "name": "Website Redesign",
        "description": "Redesign company website with modern look",
        "checklists": [
            {
                "name": "Project Tasks",
                "checkItems": [
                    {"name": "Lancey - Landing page design"},
                    {"name": "Levy - Backend optimization"},
                    {"name": "Content review - Admin"}
                ]
            }
        ],
        "recent_comments": [
            {"memberCreator": {"fullName": "Lancey Smith"}, "date": "2025-08-17T15:30:00Z", "text": "Completed wireframes"},
            {"memberCreator": {"fullName": "Criselle Admin"}, "date": "2025-08-17T14:00:00Z", "text": "Reviewed requirements"}
        ]
    },
    
    {
        "id": "card_api_docs_789",
        "name": "API Documentation",
        "description": "Create comprehensive API documentation",
        "checklists": [],  # No checklists
        "recent_comments": [
            {"memberCreator": {"fullName": "Levy Brown"}, "date": "2025-08-16T11:00:00Z", "text": "Working on endpoint documentation"},
            {"memberCreator": {"fullName": "Admin User"}, "date": "2025-08-16T10:00:00Z", "text": "This needs to be completed ASAP"}
        ]
    },
    
    {
        "id": "card_unassigned_000",
        "name": "Task Management System",
        "description": "Build internal task management tool",
        "checklists": [
            {
                "name": "Requirements",
                "checkItems": [
                    {"name": "Gather user requirements"},
                    {"name": "Design database schema"},
                    {"name": "Create UI mockups"}
                ]
            }
        ],
        "recent_comments": [
            {"memberCreator": {"fullName": "Admin User"}, "date": "2025-08-15T16:00:00Z", "text": "Project approved, need assignee"},
            {"memberCreator": {"fullName": "Criselle Manager"}, "date": "2025-08-15T15:30:00Z", "text": "Budget allocated"}
        ]
    }
]

# Expected assignment results for validation
EXPECTED_ASSIGNMENTS = {
    "explicit_assignment": {
        "mobile app": "Wendy",
        "website": "Lancey",
        "landing page": "Lancey",
        "wordpress site": "Levy"  # Should default since no explicit assignment
    },
    
    "checklist_assignment": {
        "mobile app": "Wendy",
        "website": "Lancey",
        "api": "Levy",
        "task management": "Wendy"  # Should default to mobile expert
    },
    
    "admin_filtering": {
        "mobile app": "Wendy"  # Should ignore admin/criselle assignments
    },
    
    "default_assignment_mobile": {
        "mobile": "Wendy",
        "application": "Wendy",
        "app": "Wendy"
    },
    
    "default_assignment_web": {
        "website": "Levy",
        "landing page": "Levy",
        "wordpress": "Levy"
    }
}

def run_assignment_tests():
    """Run assignment detection tests and return results."""
    print("Running Assignment Detection Tests...")
    
    test_results = {
        'passed': 0,
        'failed': 0,
        'details': []
    }
    
    for test_name, transcript in SAMPLE_TRANSCRIPTS.items():
        print(f"\nTesting: {test_name}")
        print(f"Transcript length: {len(transcript)} characters")
        
        # This would call our enhanced assignment detection
        # For now, just log the test case
        test_results['details'].append({
            'test': test_name,
            'transcript_length': len(transcript),
            'status': 'ready_for_testing'
        })
    
    return test_results

def validate_checklist_parsing():
    """Validate checklist parsing functionality."""
    print("Testing Checklist Parsing...")
    
    for card in MOCK_TRELLO_CARDS:
        print(f"\nCard: {card['name']}")
        print(f"  ID: {card['id']}")
        print(f"  Checklists: {len(card['checklists'])}")
        
        for checklist in card['checklists']:
            print(f"    - {checklist['name']}: {len(checklist['checkItems'])} items")
            for item in checklist['checkItems']:
                print(f"      * {item['name']}")

if __name__ == "__main__":
    print("TRELLO AI - Test Data Validation")
    print("="*50)
    
    # Run assignment tests
    results = run_assignment_tests()
    print(f"\nTest Summary: {results['passed']} passed, {results['failed']} failed")
    
    # Validate checklist parsing
    validate_checklist_parsing()
    
    print("\nTest data ready for integration testing!")