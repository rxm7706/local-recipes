"""Universal MCP Markitdown Server"""

__version__ = "0.1.2"

def main():
    """Main entry point for the universal_mcp_markitdown command."""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(
        description="Universal MCP Markitdown Server - Convert files and URIs to markdown format"
    )
    parser.add_argument(
        "--version", 
        action="version", 
        version=f"universal-mcp-markitdown {__version__}"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind the server to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--transport",
        default="streamable-http",
        choices=["streamable-http", "stdio"],
        help="Transport type to use (default: streamable-http)"
    )
    
    args = parser.parse_args()
    
    # Import here to avoid circular imports and allow for command-line parsing first
    from universal_mcp_markitdown.server import app_instance
    from universal_mcp.servers.server import SingleMCPServer
    
    # Create server with parsed arguments (matching the original server.py pattern)
    mcp = SingleMCPServer(
        app_instance=app_instance,
        host=args.host
    )
    
    print(f"Starting Universal MCP Markitdown Server on {args.host}")
    print(f"Transport: {args.transport}")
    print("Press Ctrl+C to stop the server")
    
    try:
        # Run the MCP server
        mcp.run(transport=args.transport)
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        sys.exit(0)

if __name__ == "__main__":
    main()
