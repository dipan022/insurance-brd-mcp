import asyncio

from mcp import Client

from server import mcp


async def main():

    print(
        "Starting MCP client..."
    )

    async with Client(mcp) as client:

        print(
            "Connected to MCP server!"
        )

        tools = (
            await client.list_tools()
        )

        print(
            "\nAvailable tools:"
        )

        for tool in tools.tools:

            print(
                "-",
                tool.name
            )

        # -----------------------------------------------
        # Test Jira READ only
        # -----------------------------------------------

        print(
            "\nTesting Jira KAN-1..."
        )

        result = await client.call_tool(
            "get_jira_issue",
            {
                "issue_key": "KAN-1"
            }
        )

        print(
            "\n===== JIRA RESULT ====="
        )

        for content in result.content:

            if (
                hasattr(
                    content,
                    "text"
                )
                and content.text
            ):

                print(
                    content.text
                )


if __name__ == "__main__":

    asyncio.run(
        main()
    )