# Run BMad in Microsoft Copilot

The BMad Method Web Bundles allow you to run structured planning skills directly within the Microsoft 365 Copilot ecosystem. By setting up a "Declarative Agent" (or Custom Copilot), you can brainstorm, draft PRDs, and perform system architecture analysis without leaving your Microsoft workflow.

Here are the step-by-step instructions for getting a Web Bundle running in Microsoft Copilot.

---

## The 6 BMad Planning Agents

You can create distinct Copilot agents for each of the 6 official Web Bundles available at [bmadcode.com/web-bundles](https://www.bmadcode.com/web-bundles/). The setup process is identical for all of them; simply download the corresponding ZIP and follow the creation steps below for each one.

1. **Brainstorming Coach:** Uses 60+ proven ideation techniques to help you formulate and refine initial concepts.
2. **Product Brief Coach:** Facilitates the creation, updating, and validation of standardized project briefs.
3. **PRFAQ Coach:** Guides you through Amazon-style "Working Backwards" press release and FAQ planning.
4. **PRD Coach:** Generates strict, structured Product Requirements Documents with built-in requirements validation.
5. **UX Coach:** Bridges the gap between design and engineering by outputting a two-spine technical spec (`DESIGN.md` for technical layout and `EXPERIENCE.md` for user journeys).
6. **Market & Industry Research:** Conducts deep competitive and industry research to serve as inputs for your technical decision-making.

---

## Method 1: Using Copilot "Agent Builder" (Quick & Easy)

This is the fastest method to build an agent right inside your normal Copilot interface without leaving your chat window.

1. **Download the Bundle:** Grab the ZIP file for the BMad skill you want from the [BMad Web Bundles page](https://www.bmadcode.com/web-bundles/) and extract it.
2. **Open Copilot:** Go to the Microsoft 365 Copilot app via your web browser at `microsoft365.com/chat` or inside Microsoft Teams.
3. **Start a New Agent:** In the right-hand navigation pane, look for the **Agents** section and click on **New Agent**.
4. **Describe the Agent:** Use the AI builder to give your agent a basic identity (e.g., "Create a Product Manager agent that uses the BMad method to write PRDs").
5. **Configure Instructions:** On the configuration screen, you'll see a spot for **Instructions**. This is where you paste the full contents of the `INSTRUCTIONS.md` file from your downloaded Web Bundle.
6. **Add Knowledge:** Click to add knowledge sources. Upload the `SKILL.md` file (and any CSVs or templates included in your bundle) here.
7. **Test & Publish:** Use the preview pane to test it out. Once it works properly, hit **Save**. You can choose to keep it private or share it with others in your organization.

---

## Method 2: Using "Microsoft Copilot Studio" (Advanced)

If you need your agent to take complex actions on your behalf (like creating Jira tickets, sending emails, or connecting to external APIs), you'll want to use Microsoft Copilot Studio.

1. **Access Studio:** Go to [copilotstudio.microsoft.com](https://copilotstudio.microsoft.com) and sign in with your M365 account.
2. **Create Agent:** Click **Create an agent** on the home page. Choose the "Advanced Create" option for full configuration control.
3. **Configure the Core:**
   * **Instructions:** Paste your Web Bundle `INSTRUCTIONS.md` into the main prompt/instructions text box.
   * **Knowledge:** Navigate to the **Knowledge** tab and upload your `SKILL.md` file. Copilot Studio allows you to connect to a wider array of enterprise data sources here if needed.
4. **Add Actions (Optional):** If you want your agent to automate processes, navigate to the **Actions** or **Topics** tabs to wire up Power Automate flows or custom API connectors.
5. **Publish:** Test your new Copilot in the chat panel, then hit **Publish**. You can deploy this agent to Teams, SharePoint, or even your company's custom websites.
