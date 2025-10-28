# PiAPI Knowledge Base

## Table of Contents
1. [Key Features](#key-features)
2. [Available APIs](#available-apis)
3. [Service Options](#service-options)
4. [Pricing & Credits](#pricing--credits)
5. [Quick Start](#quick-start)
6. [Webhook Configuration](#webhook-configuration)
7. [Make Integration Guide](#make-integration-guide)
8. [Song API Examples](#song-api-examples)
9. [API Reference](#api-reference)

---

## Key Features

### Unified API Schema
What truly sets PiAPI apart is our **unified API architecture**, which simplifies the process: with just two endpoints, you can handle the full spectrum of task creation and retrieval. For an in-depth explanation, explore our [Unified API Schema](https://piapi.ai/docs/unified-api-schema) on the unified API framework.

### Broad Model Selection
Access a diverse range of models for various AI tasks.

### Webhook Integration
We offer [Webhook](https://piapi.ai/docs/unified-webhook) services integrated with our [Unified API Schema](https://piapi.ai/docs/unified-api-schema) for timely updates and notifications.

---

## Available APIs

> **Important Notice (2025):** PiAPI has **discontinued Midjourney API service**. Users seeking Midjourney API access should visit [LegNext.ai](https://legnext.ai) for alternatives.

### Image Generation Models
- **[Flux](https://piapi.ai/flux-api)** - High-quality image generation with LoRA and ControlNet support
  - Text-to-Image
  - Image-to-Image
  - Image Variation
  - Background Removal
  - Image Restoration
  - Outpainting/Extension
- **[Faceswap](https://piapi.ai/faceswap-api)** - Advanced facial recognition and swapping technology
  - Image Faceswap
  - Video Faceswap
- **Nano Banana AI** - Additional image generation capabilities

### Video Generation Models
- **[Kling](https://piapi.ai/kling-api)** - Physics-aware cinematic video generation
  - Text-to-Video
  - Image-to-Video
  - Kling Elements
- **[Dream Machine (Luma)](https://piapi.ai/dream-machine-api)** - Cinematic-quality video generation
  - Text-to-Video ($0.20 per generation - 60% savings vs competitors)
  - Image-to-Video
  - Video Extension
  - Watermark Removal
- **[Hunyuan Video](https://piapi.ai/docs/hunyuan-video/txt2video-api)** - Fast and standard video generation options
  - Standard quality
  - Fast generation mode
- **[Skyreels V1](https://piapi.ai/skyreels)** - Human-centric video generation
  - 33 distinct facial expressions
  - 400+ movement combinations
  - First advanced open-source human-centric model
- **[Hailuo](https://piapi.ai/docs/hailuo-api/generate-video)** - Video generation capabilities
- **[AI Hug](https://piapi.ai/docs/ai-hug-api/create-task)** - Specialized emotional video generation
- **[Video Upscale](https://piapi.ai/docs/tools/video-upscale-api)** - Enhance video resolution using Qubico/video-toolkit

### 3D Generation Models
- **[Trellis 3D](https://piapi.ai/trellis-3d-api)** - State-of-the-art 3D content generation (Apache 2.0 license)
  - Text-to-3D
  - Image-to-3D
  - Commercial use allowed

### Audio & Music Models
- **[Ace Step](https://piapi.ai/ace-step)** - Text-to-music conversion
- **[Udio (music-u)](https://piapi.ai/docs/suno-api/get-task)** - Music generation with lyrics support
  - Simple Prompt Mode
  - Instrumental Mode
  - Full Lyrics Mode
- **[Suno](https://piapi.ai/docs/suno-api/get-task)** - Music generation
- **[f5-TTS](https://piapi.ai/blogs/the-best-tts-api-in-2025-f5-tts-api)** - Zero-shot text-to-speech ($0.025 per 1,000 characters)

### LLM & Conversational AI
- **[GPT-4o Image Generation](https://piapi.ai/docs/llm-api/gpt-4o-image-generation-api)** - OpenAI's image generation via LLM
- **DeepSeek** - Advanced language model capabilities
- Check [LLM API](https://piapi.ai/docs/llm-api/completions) for full details

---

## Service Options

### Pay-as-you-go (PPU)
**Pay-as-you-go**, sometimes referred to as "PPU" or "Pay-per-use", is a service option where you don't have to have your own Midjourney/ChatGPT/Kling/Luma/etc accounts depending on the API you want to use. You will be using the account pool operated by us and it will consume your **credits** (which you can get more by topping up). All the jobs submitted will be processed by our accounts.

The Pay-as-you-go service option will consume your **PiAPI credits**, which you can top up on the [Workspace](https://app.piapi.ai/).

### Host-your-account (BYOA)
**Host-your-account**, sometimes referred to as "BYOA" or "Bring-your-own-account", is a service option where you do need to have and operate your own Midjourney/ChatGPT/Kling/Luma/etc accounts, and then subscribe to a seat or multiple seats on our platform for that particular API, connect your account to that seat, and then start using the API. All the jobs submitted will be processed by your own accounts.

The Host-your-account service option will require you to **subscribe to Host-your-account seats** for that particular API you want to use. You will not need to top up PiAPI credits for Host-your-account service option.

### Reliability Best Practice
For APIs where both service options are available, the most reliable way is to use **both Pay-per-use and Host-your-account** service options to reduce the possibility of downtime associated with account operation related issues. For example, you could:
- Primarily use Pay-as-you-go and have your own Host-your-account as backup
- Use your Host-your-accounts and failover to our Pay-as-you-go (there is a toggle for this failover logic on the [Workspace](https://app.piapi.ai/))

### Host-Your-Account Seat Pricing
- **$5-$10 per seat per month** depending on the specific API
- No credit consumption for BYOA service option
- Subscribe to seats on the [Workspace](https://app.piapi.ai/)

---

## Pricing & Credits

### Subscription Plans

#### Free Plan
- Basic access to PiAPI services
- Free credits to get started
- No credit card required for trial

#### Creator Plan - $8/month
- Enhanced processing capabilities
- Monthly included credits
- Email/ticket support
- File-to-URL conversion

#### Pro Plan - $50/month
- **Unlimited task processing speed**
- **$10 FREE monthly credits included**
- Priority email and ticket support
- Free file-to-URL conversion
- Advanced features access

### Pay-As-You-Go Pricing (2025)

**Image Generation:**
- **Flux API**: $0.02 per image (only pay for successful generations)

**Video Generation:**
- **Dream Machine (Luma)**: $0.20 per video task (60% savings vs competitors)

**Audio/TTS:**
- **f5-TTS API**: $0.025 per 1,000 characters

**3D Generation:**
- **Trellis 3D**: Competitive PAYG pricing (check workspace for current rates)

### Credit System

- **Credit Validity**: 180 days from purchase date
- **Cryptocurrency Discounts**: Exclusive discounts available when paying with cryptocurrency (effective January 1, 2025)
- **No Monthly Commitment**: Flexible pay-as-you-go model with no locked-in subscriptions
- **Top-Up**: Available anytime on the [Workspace](https://app.piapi.ai/)

### Important Notes

- Only successful task completions consume credits
- Free trial credits available for new accounts
- Host-Your-Account seats are separate from PAYG credits
- Unused credits expire after 180 days

---

## Quick Start

To start using the PiAPI, follow this quickstart guide to set up your environment and make your first API call.

### 1. Generate an API Key

**What is API key?**
An API key is a secure credential that allows your code to interact with our API. Never share your API key with anyone, as it can be exploited without your knowledge.

**Steps:**
1. **Create an account**: Go to [PiAPI workspace](https://app.piapi.ai/) and log in with your GitHub account
2. **Create an API key**: After logged in, navigate to the API key in workspace and generate one

### 2. Set Base URL

This is the URL to be used for all of our API calls:

```
https://api.piapi.ai
```

### 3. Make Your First API Call

Let's take **Flux API** for an example.

#### Set URL Endpoint
With our [Unified API Schema](https://piapi.ai/docs/unified-api-schema), users could interact with all models and services through just two endpoints: `create task` and `get task`.

Here we want to create a Flux `text-to-image` task, so the endpoint should be:
```
https://api.piapi.ai/api/v1/task
```

#### Set the Header
In most cases, you will need an **API key** for authorization. Remember to replace `YOUR_API_KEY` with your own API key.

```python
headers = {
    'x-api-key': 'YOUR_API_KEY',
}
```

#### Set the Request Body
APIs of Unified API schema share the same request and response format. You will need to specify three main components:

- `model`: The specific model you wish to interact with. Here we set to `Qubico/flux1-schnell`
- `task_type`: The type of task. Here we set to `txt2img`
- `input`: The inputs specific to the task and model. `prompt` is required. Let's set to "a bear" for example

```json
{
   "model": "flux1-schnell",
   "task_type": "txt2img",
   "input": {
      "prompt": "a bear"
   }
}
```

**Tip:** For the introduction of params needed in request body, refer to the documentation of specific endpoint you want to interact with. You can check [Flux Text to Image endpoint doc](https://piapi.ai/docs/flux-api/text-to-image) about the params above.

#### Send the Request

```python
import requests
import json

url = "https://api.piapi.ai/api/v1/task"

payload = json.dumps({
   "model": "Qubico/flux1-schnell",
   "task_type": "txt2img",
   "input": {
      "prompt": "a bear",
   }
})

headers = {
   'X-API-Key': 'Your API key',
   'Content-Type': 'application/json'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)
```

And you will get a response in unified response schema. Now you have made your first API call. Happy integrating!

### Alternate Domains

Here are the available domains for all of our API endpoints. We recommend you to experiment with them and change the domains as needed:

1. **api.piapi.ai** - the primary domain for all API endpoints

---

## Webhook Configuration

PiAPI offers webhook integration for real-time notifications when tasks complete or fail.

### Overview

When you create a task, you can specify a webhook endpoint. PiAPI will send an HTTP POST request to this URL whenever a task succeeds or fails.

### Configuration Structure

Include a `webhook_config` object in your task creation request:

```json
{
  "model": "flux1-schnell",
  "task_type": "txt2img",
  "input": {
    "prompt": "a bear"
  },
  "config": {
    "webhook_config": {
      "endpoint": "https://your-domain.com/webhook",
      "secret": "your-secret-key"
    }
  }
}
```

### Endpoint Requirements

1. **Protocol**:
   - **Development**: HTTP or HTTPS
   - **Production**: HTTPS required for security

2. **Response Requirements**:
   - Always respond with a **2xx status code** before performing any extended logic
   - Quick acknowledgment prevents timeout issues

3. **Payload**:
   - Accepts POST requests with JSON payload
   - Contains complete task information including status, output, and metadata

### Retry Mechanism

If PiAPI does not receive a successful response (status 2xx) or encounters a 4xx or 5xx error:
- **Retry Delay**: 5 seconds after failed attempt
- **Maximum Attempts**: 3 attempts total per notification
- **Behavior**: Task status updates even if webhook fails

### Security Best Practices

1. **Use HTTPS in Production**
   - Protects data in transit
   - Prevents unauthorized access
   - Required for production environments

2. **Verify Request Timestamp**
   - Compare request timestamp with current system time
   - Reject requests with excessive time differences (e.g., > 5 minutes)
   - Prevents replay attacks

3. **Validate Secret Token**
   - Use the `secret` field to verify requests originate from PiAPI
   - Compare against your stored secret key
   - Reject requests with invalid or missing secrets

4. **Implement Idempotency**
   - Use `task_id` to track processed webhooks
   - Prevent duplicate processing if retry occurs
   - Store processed task IDs temporarily

### Example Webhook Payload

```json
{
  "code": 200,
  "data": {
    "task_id": "7088bf9d-6edb-4fab-b1fd-83afc64dde91",
    "model": "flux1-schnell",
    "task_type": "txt2img",
    "status": "completed",
    "input": {
      "prompt": "a bear"
    },
    "output": {
      "image_url": "https://cdn.piapi.ai/result/image.png"
    },
    "meta": {
      "created_at": "2025-01-15T10:30:00Z",
      "started_at": "2025-01-15T10:30:05Z",
      "ended_at": "2025-01-15T10:30:25Z",
      "usage": {
        "type": "credit",
        "frozen": 0.02,
        "consume": 0.02
      }
    }
  }
}
```

### Testing Webhooks

1. Use services like [Webhook.site](https://webhook.site) or [RequestBin](https://requestbin.com) for testing
2. Start with development endpoints before production
3. Monitor retry attempts in PiAPI workspace logs
4. Verify payload structure matches expectations

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Webhooks not received | Verify endpoint is publicly accessible and returns 2xx |
| Timeout errors | Respond with 2xx immediately, process asynchronously |
| Duplicate webhooks | Implement idempotency using task_id |
| Security concerns | Use HTTPS, validate secret, check timestamps |

For more details, visit the [Unified Webhook Documentation](https://piapi.ai/docs/unified-webhook).

---

## Make Integration Guide

### Introduction

Recently, to help more content creators easily use PiAPI for their projects, **Flux** by PiAPI has officially launched on the Make platform!

For content creators or anyone without coding background who find API concepts challenging, this documentation will use visual guides to help you overcome these challenges.

**Topics Covered:**
1. Finding PiAPI's Flux Modules on Make Platform
2. Calling APIs on the PiAPI Platform
3. Understanding PiAPI's Endpoint Structure
4. Using the Flux App (PiAPI on Make) and Integrating It into your Workflow
5. Adjusting Module Parameters and Their Meanings: Flux Module Selection and Parameter Configuration Guide
6. Building a Simple Workflow Using PiAPI on Make

**Join the Community:**
- Share your workflow output on social media with us
- Join our [Discord](https://discord.com) to discuss!

### Finding PiAPI's Flux Modules on Make

1. Log in to the Make platform
2. Locate **Scenarios** in the left Dashboard
3. Click **Create Apps** to enter the main workflow builder interface
4. Search for "PiAPI/Flux" and you'll see the Flux API modules available for use

### Understanding PiAPI's Endpoint Structure

Before organizing your workflow automation, familiarize yourself with:

**Core Concepts:**
- API Structure and its components
- Purpose of each structural element
- Endpoint Types and their functions
- Parameter Definitions and requirements
- Best Practices for executing flawless API calls

An endpoint in PiAPI consists of three core components:

#### 1. URL
The service path that directs your request.

- **Key Requirement**: You must use the correct address to successfully reach PiAPI
- **HTTP Methods**:
  - `POST` - Used when you need to create a task
  - `GET` - Used when retrieving task response

**Important:** If you want to make an API call to send your request to Flux API, then you should choose POST. If you want to fetch your response, you should choose GET and send URL and Header Params to get your response (especially when you need to check or use an output in your workflow) in a specific task you have initiated.

#### 2. Header Params
- Usually includes your X-API-Key

#### 3. Body Params
- Model
- Task-type
- Input
  - prompt
  - width
  - height
  - (additional parameters vary by model and task-type)

**Tip:** Usually the input params are mainly based on the model and task-type. Check the section **Flux Module Selection and Parameter Configuration Guide** to see the params that could be included when you choose different task-type based on your need.

### How to Make an API Call in PiAPI

In PiAPI, you have two methods to call Flux APIs (applicable to other APIs as well):

1. **Using Playground**: Fill in the required parameters for direct execution
2. **Via Run API**: Submit your API call, then retrieve the task results from the respective model's Task History section

When using the Run API to call PiAPI platform APIs, you'll have a broader range of options. As mentioned earlier regarding API call structures, you can:
1. Refer to the parameter specifications below for task_type selection
2. Configure input parameters according to your requirements

Through understanding the structure of every API request, you can create an API call on your own. Isn't that difficult, right? 💪

### How to Make an API Call in Make

According to HTTP methods which depends on whether you want to create a task (POST) or get your task response (GET).

#### Set up a POST Module

1. **Connect your PiAPI account**
   - Make sure you're logged in first
2. **Prepare your request**
   - Create a JSON module (this is where you type your settings)
   - A JSON Module contains the structure of an endpoint's body including model, task-type and input
   - In this step, you need to construct your data structure based on the endpoint on your own

#### Set up a GET Request

1. **Connect your PiAPI account**
   - Ensure you're properly logged in
2. **Select the API call node**
   - Choose "Make an API Call" from available options
3. **Configure the request**
   - URL: Enter `/v1/task/` followed by your specific task_id (Example: `/v1/task/12345`)
   - Method: Select `GET`
4. **Run the request**
   - Execute to retrieve your task results

### Flux Module Selection and Parameter Configuration Guide

#### What is LoRA?
LoRA is a style filter for AI art. To choose a LoRA, check the available styles in [PiAPI's Flux Documentation](https://piapi.ai/docs/available-lora-and-controlnet).

#### What is ControlNet?
ControlNet is a neural network structure designed to precisely control AI image generation by incorporating additional input conditions (e.g., edge maps, depth maps, human poses). It acts as a "steering wheel" for models like Stable Diffusion, ensuring generated images strictly adhere to structural constraints while following text prompts.

Check [PiAPI's Flux Documentation](https://piapi.ai/docs/available-lora-and-controlnet) to get ControlNet type.

### Module Types and Parameter Configuration

#### Extend an Image
Expands the boundaries of an image. The user uploads an image, and the system generates new background or scenery based on the original content. Suitable for extending the image's view into a broader scene.

| Parameter Name    | Description | Constraints & Details |
|-------------------|-------------|----------------------|
| `image`          | Image URL | URL format |
| `prompt`         | Content to show in the extended part | string |
| `outpaint_left`  | Expand canvas pixels to the left | Total delta pixel size < 1024×1024 |
| `outpaint_right` | Expand canvas pixels to the right | Total delta pixel size < 1024×1024 |
| `outpaint_top`   | Expand canvas pixels to the top | Total delta pixel size < 1024×1024 |
| `outpaint_bottom`| Expand canvas pixels to the bottom | Total delta pixel size < 1024×1024 |
| `denoise`        | Controls noise/artifact removal strength in AI-generated images | Range: 0.1 to 1 |
| `guidance_scale` | Adjusts adherence between generated content and text prompt | Range: 1.5 to 5.0 |

#### Generate an Image from an Image
Generates a new image based on an input image. The user uploads an existing image, and the system modifies or transforms it to generate a new version.

| Parameter Name      | Description | Constraints & Details |
|---------------------|-------------|----------------------|
| `image`            | Image URL | URL format |
| `prompt`           | Content to display in the extended part | string (Example: "A lovely puppy") |
| `negative_prompt`  | Elements to avoid during generation | string |
| `denoise`          | Proportion of input images (controls noise removal) | float (0.1-1.0) |
| `guidance_scale`   | Controls adherence between generated content and text prompt | float (1.5-5.0) |

#### Generate an Image from an Image with LoRA
Generates a modified image based on the LoRA model.

| Parameter         | Description | Constraints & Details |
|-------------------|-------------|----------------------|
| `Image`          | Image URL | URL format |
| `Prompt`         | Desired image description | string (Example: "A lovely puppy") |
| `Lora_type`      | Art style selection | Choose from PiAPI's available LoRA options |
| `Lora_strength`  | LoRA style intensity | Range: 0.1 (faint) to 1.0 (strong) |
| `Guidance_scale` | Prompt adherence level | Range: 1.5 (creative) to 5.0 (strict) |
| `Negative_prompt`| Elements to exclude | Optional (Example: "blurry, distorted hands") |
| `Width`/`Height`| Image dimensions | In pixels (e.g., 1024×768), Max: 2048×2048 |

#### Generate an Image from Text
Creates an image based on a text description.

| Parameter Name     | Description | Constraints & Details |
|--------------------|-------------|----------------------|
| `Batch_size`      | Batch image generation count | Type: Integer, Range: 1 to 4, Default: 1 |
| `image`           | Source image URL | Type: String (URL format) |
| `prompt`          | Description of desired image content | string (Example: "A lovely puppy") |
| `negative_prompt` | Elements to avoid in generation | Optional |
| `guidance_scale`  | Controls prompt adherence strength | Range: 1.5 to 5.0 |

#### Generate Image with Text based on LoRA
Creates an image based on a text description using LoRA for fine-tuned generation.

| Parameter        | Description | Details & Constraints |
|------------------|-------------|-----------------------|
| **Prompt**       | Describe your desired image | string (Example: "A lovely puppy") |
| **Lora_type**    | Select an art style | Available PiAPI LoRA options |
| **Lora_strength**| LoRA style effect intensity | Default: 1.0 (maximum effect), Range: 0.1 (faint) - 1.0 (strong) |
| **Guidance_scale**| AI prompt adherence level | Range: 1.5 (random) - 5.0 (strict) |
| **Negative_prompt**| Elements to exclude | Optional (Example: "blurry, distorted hands") |
| **Width/Height** | Output image dimensions | In pixels (e.g., 1024×768) |

#### Generate an Image with ControlNet and LoRA
Generates an image using ControlNet and LoRA.

| Parameter         | Description | Constraints & Details |
|-------------------|-------------|-----------------------|
| **Image**        | Source image URL | URL format |
| **Prompt**       | Desired image description | string (Example: "A lovely puppy") |
| **control_type** | ControlNet type | `depth` (default), `soft_edge`, `canny`, `openpose` |
| **control_strength** | ControlNet effect intensity | Range: 0.0 - 5.0 |
| **Lora_type**    | Art style selection | Select from PiAPI's LoRA options |
| **Lora_strength**| LoRA style intensity | Range: 0.1 (faint) - 1.0 (strong) |
| **denoise**      | Input image proportion | Range: 0.1 - 1.0 |
| **Guidance_scale**| Prompt adherence level | Range: 0.0 (random) - 5.0 (strict) |

#### Generate a Variation of an Image
Creates a new variation of an image based on the original input.

| Parameter        | Description | Constraints & Details |
|------------------|-------------|-----------------------|
| **Batch_size**  | Batch image generation count | Default: 1, Range: 1-4 |
| **image**       | Source image URL | Valid URL |
| **prompt**      | Content for extended image part | string (Example: "A lovely puppy") |
| **width**       | Image length in pixels | Recommended: ≤2048 |
| **height**      | Image width in pixels | Recommended: ≤2048 |
| **denoise**     | Noise removal strength | Range: 0.1-1.0 |
| **guidance_scale**| Prompt adherence strength | Range: 0.0-5.0 |

#### Remove the Background from an Image
Removes the background from an image, leaving a transparent or solid-color background.

| Parameter  | Type     | Description          | Example              |
|-----------|----------|----------------------|----------------------|
| `image`   | `string` | Source image URL     | `https://example.com/image.jpg` |

#### Restore an Image
Restores a damaged image. The user uploads an image with some parts missing or damaged, and the system fills in these gaps based on the user's description.

| Parameter         | Description | Constraints & Details |
|-------------------|-------------|-----------------------|
| **Batch_size**   | Batch image generation count | Default: 1, Range: 1-4 |
| **image**        | Source image URL | Valid URL format |
| **prompt**       | Content for extended image part | string (Example: "A lovely puppy") |
| **denoise**      | Noise/artifact removal strength | Range: 0.1-1.0 |
| **guidance_scale**| Prompt adherence strength | Default: 2.5, Range: 0.0-5.0 |
| **service_mode** | Payment method selection | `ppu` (pay-per-use), `byoa` (bring-your-own-account) |

### Building a Simple Workflow Using PiAPI on Make

**Example Workflow: Google Sheets + Flux API**

1. **Set up Google Sheet**
   - Input your parameters (such as prompt and lora_strength) into a Google Sheet based on your selected module type

2. **Add Google Sheet Trigger**
   - Choose "Watch New Rows" trigger (workflow executes when new row data is added)
   - Set "Limit" to determine how many rows are fetched per execution (e.g., 1 row at a time)

3. **Add Flux Node**
   - Input all required parameters from the Google Sheet

4. **Add Output Capture Node**
   - Select "Update a Row" to automatically store the target image's URL at the end of the input row upon workflow completion
   - This ensures seamless traceability by appending results directly to your Google Sheet

5. **Run the Workflow**
   - Click "Run Once"
   - Check the URL feedback in the Google Sheet

---

## Song API Examples

This section provides examples and descriptions for tasks supported by the Song API.

### Music-u (Udio API)

Currently, the `music-u` model supports only the `generate_music` task. Below are the task examples for different use cases:

#### Udio Simple Prompt
This mode generates music based on a textual description prompt. It is similar to Suno's description mode.

```json
{
    "model": "music-u",
    "task_type": "generate_music",
    "input": {
        "gpt_description_prompt": "night breeze, piano",
        "negative_tags": "",
        "lyrics_type": "generate",
        "seed": -1
    },
    "config": {
        "service_mode": "public",
        "webhook_config": {
            "endpoint": "",
            "secret": ""
        }
    }
}
```

#### Udio Instrumental
This mode generates instrumental music.

```json
{
    "model": "music-u",
    "task_type": "generate_music",
    "input": {
        "gpt_description_prompt": "night breeze",
        "negative_tags": "",
        "lyrics_type": "instrumental",
        "seed": -1
    },
    "config": {
        "service_mode": "public",
        "webhook_config": {
            "endpoint": "",
            "secret": ""
        }
    }
}
```

#### Udio Full Lyrics
This mode generates music using user-provided lyrics.

```json
{
    "model": "music-u",
    "task_type": "generate_music",
    "input": {
        "lyrics": "[Verse]\nIn the gentle evening air,\nWhispers dance without a care.\nStars ignite our dreams above,\nWrapped in warmth, we find our love.\n[Chorus]\n",
        "gpt_description_prompt": "jazz, pop",
        "negative_tags": "",
        "lyrics_type": "user",
        "seed": -1
    },
    "config": {
        "service_mode": "public",
        "webhook_config": {
            "endpoint": "",
            "secret": ""
        }
    }
}
```

---

## API Reference

### Unified API Endpoints

PiAPI's unified API architecture provides just **two core endpoints** for all models and services:

#### 1. Create Task Endpoint

**Endpoint:** `POST https://api.piapi.ai/api/v1/task`

Creates a new task for any supported model (Flux, Kling, Dream Machine, Udio, etc.)

**Purpose:** Submit jobs for image generation, video generation, music creation, 3D modeling, and more.

**Request Structure:**
```json
{
  "model": "string",           // e.g., "flux1-schnell", "kling", "music-u"
  "task_type": "string",       // e.g., "txt2img", "txt2video", "generate_music"
  "input": {                   // Model-specific parameters
    "prompt": "string",
    // ... additional parameters
  },
  "config": {                  // Optional configuration
    "service_mode": "public",  // or "byoa" for Host-Your-Account
    "webhook_config": {
      "endpoint": "string",
      "secret": "string"
    }
  }
}
```

**Response:**
- Returns a `task_id` immediately
- Task processes asynchronously
- Use the Get Task endpoint to retrieve results

#### 2. Get Task Endpoint

**Endpoint:** `GET https://api.piapi.ai/api/v1/task/{task_id}`

This endpoint retrieves the status and output of a previously created task.

#### Request Parameters

**Path Parameters:**
- `task_id` (required): The unique identifier for the task

**Header Parameters:**
- `x-api-key` (required): Your API Key used for request authorization

#### Response Schema

**Success Response (200):**

```json
{
    "code": 200,
    "data": {
        "task_id": "string",
        "model": "string",
        "task_type": "string",
        "status": "Completed|Processing|Pending|Failed|Staged",
        "input": {},
        "output": {},
        "meta": {
            "created_at": "string",
            "started_at": "string",
            "ended_at": "string",
            "usage": {
                "type": "string",
                "frozen": 0,
                "consume": 0
            },
            "is_using_private_pool": false
        },
        "detail": null,
        "logs": [],
        "error": {
            "code": 0,
            "message": "string"
        }
    },
    "message": "success"
}
```

#### Status Codes

- **Completed**: Task has finished successfully
- **Processing**: Your job is currently being processed. Number of "processing" jobs counts as part of the "concurrent jobs"
- **Pending**: We recognize the jobs you sent should be processed but right now none of the accounts is available to receive further jobs. During peak loads there can be longer wait time to get your jobs from "pending" to "processing". Number of "pending" jobs counts as part of the "concurrent jobs"
- **Failed**: Task failed. Check the error message for detail
- **Staged**: *(Deprecated - was Midjourney only)* You have exceeded the number of your "concurrent jobs" limit and your jobs are being queued. Number of "staged" jobs does not count as part of the "concurrent jobs". Maximum number of jobs in the "staged" queue was 50

#### Concurrent Jobs & Rate Limits

**Concurrent Job Limits:**
- Both "Processing" and "Pending" jobs count toward your concurrent job limit
- "Staged" jobs (deprecated) did not count toward the limit
- Limits vary by subscription plan (check your workspace for current limits)

**Best Practices:**
- Monitor your concurrent job usage in the workspace
- Implement queuing logic if your needs exceed platform limits
- For high-volume operations, consider Host-Your-Account option for dedicated capacity
- Use webhooks to get notified when tasks complete and free up job slots

#### Metadata Fields

- **created_at**: The time when the task was submitted to us (staged and/or pending)
- **started_at**: The time when the task started processing. The time from created_at to started_at is the time the job spent in the "staged" and/or "pending" stage if there were any
- **ended_at**: The time when the task finished processing

#### Error Handling

If you get a non-null error message, follow these steps:
1. Check our [common error messages](https://climbing-adapter-afb.notion.site/Common-Error-Messages-6d108f5a8f644238b05ca50d47bbb0f4)
2. Retry several times
3. If you have retried more than 3 times and it still doesn't work, file a ticket on Discord and our support will assist you

### Example Response (Suno API)

```json
{
    "code": 200,
    "data": {
        "task_id": "7088bf9d-6edb-4fab-b1fd-83afc64dde91",
        "model": "suno",
        "task_type": "generate_music",
        "status": "completed",
        "config": {
            "service_mode": "public",
            "webhook_config": {
                "endpoint": "",
                "secret": ""
            }
        },
        "input": {},
        "output": {
            "clips": {
                "a43c955a-3474-47f3-a550-57bf7c395c48": {
                    "id": "",
                    "video_url": "https://xxx.mp4",
                    "audio_url": "https://xxx.mp3",
                    "image_url": "https://xxx.jpeg",
                    "image_large_url": "https://xxx.jpeg",
                    "is_video_pending": false,
                    "major_model_version": "v3",
                    "model_name": "chirp-v3",
                    "metadata": {
                        "tags": "",
                        "prompt": "",
                        "gpt_description_prompt": "",
                        "audio_prompt_id": "",
                        "history": null,
                        "concat_history": null,
                        "type": "gen",
                        "duration": 102,
                        "refund_credits": false,
                        "stream": true,
                        "error_type": "",
                        "error_message": ""
                    },
                    "is_liked": false,
                    "user_id": "",
                    "display_name": "",
                    "handle": "",
                    "is_handle_updated": false,
                    "is_trashed": false,
                    "reaction": null,
                    "created_at": "",
                    "status": "complete",
                    "title": "",
                    "play_count": 0,
                    "upvote_count": 0,
                    "is_public": false
                }
            }
        },
        "meta": {},
        "detail": null,
        "logs": [],
        "error": {
            "code": 0,
            "raw_message": "",
            "message": "",
            "detail": null
        }
    },
    "message": "success"
}
```

---

## MCP Integration (Model Context Protocol)

PiAPI provides MCP server integration for seamless use with Claude and other MCP-compatible applications.

### Available via MCP

The PiAPI MCP Server enables you to:
- Generate images with Midjourney, Flux, and other models
- Create videos with Kling, Dream Machine, Hunyuan, and Skyreels
- Generate 3D models with Trellis
- Create music with Udio and Suno
- Perform face swaps and image upscaling
- Access TTS (text-to-speech) capabilities

### MCP Server Implementation

**GitHub Repository:** [apinetwork/piapi-mcp-server](https://github.com/apinetwork/piapi-mcp-server)

A TypeScript implementation of a Model Context Protocol (MCP) server that integrates with PiAPI's API, enabling direct media generation from Claude or any MCP-compatible application.

### Supported Models via MCP

- **Image Generation**: Midjourney, Flux, Faceswap
- **Video Generation**: Kling, Dream Machine (Luma), Hunyuan, Skyreels, Hailuo
- **3D Modeling**: Trellis (text-to-3D, image-to-3D)
- **Audio**: Udio, Suno, Chirp, f5-TTS
- **Tools**: Video/Image upscaling, background removal

### Setup

1. Install the MCP server package
2. Configure your PiAPI API key
3. Connect to Claude or other MCP-compatible apps
4. Start generating content via natural language

For detailed setup instructions, visit the [MCP Server List](https://mcp-server-list.com/servers/piapi).

---

## Integration Platforms

### n8n Community Node

PiAPI offers an n8n community node for workflow automation:
- Text-to-image, video generation, and 3D modeling
- Faceswap, audio, TTS, and upscaling
- Visual workflow builder integration
- No-code automation capabilities

Learn more on the [n8n Community Forum](https://community.n8n.io/t/n8n-community-node-piapi).

### Make Platform Integration

Full Flux API integration available on Make platform for visual workflow automation. See the [Make Integration Guide](#make-integration-guide) section above for details.

---

## Community & Support

### Discord Community

Join our Discord community to:
- Showcase your work
- Get troubleshooting help
- Share creative workflows
- Engage in friendly and constructive discussions
- Get updates on new features and models

### Support Resources

- **Documentation**: [docs.piapi.ai](https://piapi.ai/docs/overview)
- **Homepage**: [piapi.ai](https://piapi.ai)
- **GitHub**: [PiAPI MCP Server](https://github.com/apinetwork/piapi-mcp-server)
- **Hugging Face**: [PiAPI Organization](https://huggingface.co/PiAPI)
- **Support**: Email/ticket support (Pro Plan), Community Discord

### Error Handling Resources

- [Common Error Messages](https://climbing-adapter-afb.notion.site/Common-Error-Messages-6d108f5a8f644238b05ca50d47bbb0f4)
- Retry mechanism documentation
- Discord support channel

We look forward to seeing your creative workflows! 🙌

---

## Important Updates & Notices

### January 2025 Updates

1. **Midjourney API Discontinued**: PiAPI no longer provides Midjourney API. Visit [LegNext.ai](https://legnext.ai) for alternatives.

2. **Cryptocurrency Payment Discounts**: Exclusive discounts now available when paying with cryptocurrency (effective January 1, 2025).

3. **New Models Added**:
   - Skyreels V1 (human-centric video generation)
   - Trellis 3D (text-to-3D and image-to-3D)
   - f5-TTS (advanced text-to-speech)
   - DeepSeek (LLM capabilities)

4. **Pricing Updates**: Refer to the [Pricing Update Announcement](https://piapi.ai/docs/announcements/2025-jan-pricing-update) for details.

### Best Practices Summary

1. **API Usage**:
   - Use webhooks for real-time notifications
   - Implement proper error handling and retries
   - Monitor concurrent job limits in workspace
   - Store task_ids for result retrieval

2. **Cost Optimization**:
   - Use Host-Your-Account for high-volume operations
   - Take advantage of cryptocurrency discounts
   - Monitor credit usage via workspace dashboard
   - Only pay for successful generations

3. **Reliability**:
   - Combine Pay-as-you-go and Host-Your-Account for redundancy
   - Implement failover logic
   - Use webhook retry mechanism
   - Monitor task status regularly

4. **Security**:
   - Use HTTPS in production
   - Validate webhook signatures
   - Store API keys securely
   - Implement rate limiting on your end
