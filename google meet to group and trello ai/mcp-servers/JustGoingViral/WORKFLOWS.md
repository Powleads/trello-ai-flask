# JustGoingViral MCP Server Workflows

This document provides recommended workflows and best practices for using the 69-in-1 JustGoingViral MCP server.

## Core Principles

1.  **Start with High-Level Thinking:** For any complex task, begin by using the `eesystem` or `sequentialthinking` tools to break down the problem and create a plan. This will help you choose the right tools for the job.

2.  **Combine Tools for Powerful Automation:** The real power of this server comes from chaining tools together. Don't be afraid to use multiple tools in sequence to automate complex processes.

3.  **Use the Right Tool for the Job:** With 69 tools at your disposal, there's likely a specialized tool for what you're trying to do. Refer to the `README.md` to find the best tool for your needs.

4.  **Iterate and Refine:** Don't expect to get everything perfect on the first try. Use the tools to build, test, and refine your work. The browser auditing tools and knowledge graph are great for this.

## Example Workflows

### 1. Web Development Workflow

This workflow shows how to build and deploy a simple web application.

1.  **Research:** Use `webSearch` to find a JavaScript library for a specific task (e.g., "javascript library for creating charts").
2.  **Documentation:** Use `resolve-library-id` and `get-library-docs` to get the documentation for the chosen library.
3.  **Scaffolding:** Use `create_directory` to create a project folder (e.g., `my-chart-app`).
4.  **Development:** Use `write_file` to create `index.html`, `style.css`, and `app.js` files within the new directory. Use `edit_file` to add your code.
5.  **Auditing:** Use `runPerformanceAudit` and `runAccessibilityAudit` to check the quality of your application.
6.  **Version Control:** Use `create_repository` to create a new GitHub repository.
7.  **Deployment:** Use `push_files` to commit your code to the new repository.

### 2. Task Management Workflow

This workflow shows how to manage a task from an email to completion.

1.  **Task Creation:** Use `mail` to read an email containing a new task.
2.  **Project Management:** Use `create_item` to create a new task in your Monday.com board.
3.  **Planning:** Use `eesystem` to break down the task into smaller, manageable steps.
4.  **Execution:** Use the appropriate tools to complete the task (e.g., `write_file`, `edit_file`, `webSearch`).
5.  **Progress Updates:** Use `create_update` to post progress updates to the Monday.com task.
6.  **Completion:** Use `change_item_column_values` to mark the task as "Done" in Monday.com.

### 3. Knowledge Management Workflow

This workflow shows how to research a topic and store it for later use.

1.  **Research:** Use `webSearch` to gather information on a topic.
2.  **Knowledge Graph:** Use `create_entities` and `create_relations` to store the key concepts and their relationships in your knowledge graph.
3.  **Summarization:** Use `notes` to create a summary of your research in Apple Notes.
4.  **Retrieval:** Use `search_nodes` to query your knowledge graph for information on the topic in the future.
