# Realtime API Async Python Assistant

This project demonstrates the use of OpenAI's Realtime API to create an AI assistant capable of handling voice input, performing various tasks, and providing audio responses. It showcases the integration of tools, structured output responses, and real-time interaction.

## Features

- Real-time voice interaction with an AI assistant
- Integration with OpenAI's GPT-4o Realtime API
- Asynchronous audio input and output handling
- Custom function execution based on user requests
- Visual interface for audio volume visualization
- Structured output processing for efficient data handling
- File management capabilities (create, update, delete)
- Browser interaction for web-related tasks
- Task delegation to multiple teams of AI agents

## Available Tools

- **SendMessage**: Delegates tasks to agencies, or to specific agents within agencies.

- **GetGmailSummary**: Provides a concise summary of unread Gmail messages from the past 48 hours.
- **DraftGmail**: Composes email drafts, either as a reply to an email from GetGmailSummary, or as a new message.
- **GetScreenDescription**: Captures and analyzes the current screen content for the assistant.

- **CreateFile**: Generates new files with user-specified content.
- **UpdateFile**: Modifies existing files with new content.
- **DeleteFile**: Removes specified files from the system.

- **OpenBrowser**: Launches a web browser with a given URL.
- **GetCurrentTime**: Retrieves and reports the current time.

## Setup

### MacOS Installation

1. Install [uv](https://docs.astral.sh/uv/), a modern Python package manager.
2. Clone this repository to your local machine.
3. Create a local environment file: `cp .env.sample .env`
4. Insert your `OPENAI_API_KEY` into the `.env` file.
5. Customize `personalization.json` and `config.py` to your preferences.
6. Install the required audio library: `brew install portaudio`
7. Install project dependencies: `uv sync`
8. Launch the assistant: `uv run main`

### Google Cloud API Configuration

To enable Google Cloud API integration, follow these steps:

1. Create OAuth 2.0 Client IDs in the Google Cloud Console.
2. Place the `credentials.json` file in the project's root directory.
3. Configure `http://localhost:8080/` as an Authorized Redirect URI in your Google Cloud project settings.
4. Set the OAuth consent screen to "Internal" user type.
5. Enable the following APIs and scopes in your Google Cloud project:
   - Gmail API
     - `https://www.googleapis.com/auth/gmail.readonly`
     - `https://www.googleapis.com/auth/gmail.compose`
     - `https://www.googleapis.com/auth/gmail.modify`
   - Google Calendar API
     - `https://www.googleapis.com/auth/calendar.readonly`

## Configuration

The project relies on environment variables and a `personalization.json` file for configuration. Ensure you have set up:

- `OPENAI_API_KEY`: Your personal OpenAI API key
- `PERSONALIZATION_FILE`: Path to your customized personalization JSON file
- `SCRATCH_PAD_DIR`: Directory for temporary file storage

## Usage

After launching the assistant, interact using voice commands. Example interactions:

1. "What time is it now?"
2. "Open ChatGPT in my browser."
3. "Create a new file named user_data.txt with some example content."
4. "Update the user_data.txt file by adding more information."
5. "Delete the user_data.txt file."

## Code Structure

### Core Components

- `main.py`: Application entry point
- `agencies/`: Agency-Swarm teams of specialized agents
- `tools/`: Standalone tools for various functions
- `config.py`: Configuration settings and environment variable management
- `visual_interface.py`: Visual interface for audio energy visualization
- `websocket_handler.py`: WebSocket event and message processing

### Key Features

1. **Asynchronous WebSocket Communication**:
   Utilizes `websockets` for asynchronous connection with the OpenAI Realtime API.

2. **Audio Input/Output Handling**:
   `AsyncMicrophone` class manages real-time audio capture and playback.

3. **Function Execution**:
   Standalone tools in `tools/` are invoked by the AI assistant based on user requests.

4. **Structured Output Processing**:
   OpenAI's Structured Outputs are used to generate precise, structured responses.

5. **Visual Interface**:
   PyGame-based interface provides real-time visualization of audio volume.

## Extending Functionality

### Adding Standalone Tools

Standalone tools are independent functions not associated with specific agents or agencies.

To add a new standalone tool:
1. Create a new file in the `tools/` directory.
2. Implement the `run` method using async syntax, utilizing `asyncio.to_thread` for blocking operations.
3. Install any necessary dependencies: `uv add <package_name>`

### Adding New Agencies

Agencies are Agency-Swarm style teams of specialized agents working together on complex tasks.

To add a new agency:
1. Drag-and-drop your agency folder into the `agencies/` directory.
2. Install any required dependencies: `uv add <package_name>`

## Development Roadmap

- [x] Implement standalone tools
- [x] Complete agency integration
- [ ] Develop interruption handling for smoother conversations
- [ ] Implement transcript logging for conversation tracking
- [ ] Convert `personalization.json` to a Pydantic model for improved type safety
- [ ] Enable parallel execution of tools for increased efficiency
- [ ] Resolve audio cutoff issues at the end of responses

## Additional Resources

- [OpenAI Realtime API Documentation](https://platform.openai.com/docs/guides/realtime)
- [OpenAI Structured Outputs Guide](https://platform.openai.com/docs/guides/structured-outputs)
- [WebSockets Library for Python](https://websockets.readthedocs.io/)
- [PyAudio Documentation](https://people.csail.mit.edu/hubert/pyaudio/docs/)
- [Pygame Documentation](https://www.pygame.org/docs/)
