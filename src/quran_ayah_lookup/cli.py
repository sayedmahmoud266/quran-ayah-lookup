"""
CLI module for quran-ayah-lookup package.

Provides command-line interface for interacting with the Quran database.
"""
import sys
import click
from typing import Optional

# set package setting to not automtically load on import
from .models import default_settings
default_settings.autoload_on_import = False

# Import the package functionality
from . import (
    get_verse,
    get_surah,
    search_text,
    fuzzy_search,
    search_sliding_window,
    smart_search,
    get_surah_verses,
    get_quran_database,
    initialize_quran_database,
    QuranStyle,
)

def style_option(f):
    """Click option for selecting Quran style/version."""
    @click.option("--style", "-s", type=click.Choice([style.name for style in QuranStyle]), default=None, help="Quran text style/version to use")
    @click.pass_context
    def wrapper(ctx, style, *args, **kwargs):
        ctx.ensure_object(dict)
        
        # 1. Check if style was provided at THIS level
        if style is not None:
            ctx.obj['SELECTED_STYLE'] = style
        
        # 2. Retrieve the most recent style from context
        current_style_name = ctx.obj.get('SELECTED_STYLE')

        if current_style_name:
            selected_style = QuranStyle[current_style_name]
            default_settings.style = selected_style
            
            # 3. Only initialize if it's not already set to this
            # This prevents the "Group" and "Command" from double-initializing
            print(f"Initializing Quran database with style: {selected_style.name}")
            initialize_quran_database(selected_style)
        
        # 4. IMPORTANT: If 'f' is a command that expects 'style', 
        # we must put it back into kwargs or it disappears.
        # However, since we use @click.pass_context, we can just pass ctx.
        return ctx.invoke(f, *args, **kwargs)
    return wrapper


@click.group(invoke_without_command=True, help="Quran Ayah Lookup CLI - Look up Quranic ayahs, search text, and perform fuzzy searches using the Quran corpus from Tanzil.net.")
@click.version_option()
@style_option
def cli():
    """
    Quran Ayah Lookup CLI
    
    A command-line interface for looking up Quranic ayahs, searching Arabic text,
    and performing fuzzy searches. Uses Quran corpus from Tanzil.net.
    
    If no command is provided, starts an interactive REPL mode.
    """
    ctx = click.get_current_context()
    if ctx.invoked_subcommand is None:
        # No subcommand provided, start REPL mode
        repl_mode()


@cli.command(name="verse", help="Get a specific verse by surah and ayah number")
@click.argument("surah", type=int)
@click.argument("ayah", type=int)
@click.option("--normalized", "-n", is_flag=True, help="Show normalized text only")
@click.option("--original", "-o", is_flag=True, help="Show original text only")
@style_option
@click.pass_context
def get_verse_cmd(ctx, surah: int, ayah: int, normalized: bool, original: bool):
    """
    Get a specific verse by surah and ayah number.
    
    Examples:
        qal verse 3 35          # Get Al-Imran, verse 35
        qal verse 1 1 --normalized  # Show normalized text only
    """    
    try:
        verse = get_verse(surah, ayah)
        display_verse(verse, normalized=normalized, original=original)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command(name="surah", help="Get information about a specific surah/chapter")
@click.argument("surah_number", type=int)
@click.option("--count", "-c", is_flag=True, help="Show verse count only")
@click.option("--list", "-l", is_flag=True, help="List all verses")
@style_option
@click.pass_context
def get_surah_cmd(ctx, surah_number: int, count: bool, list: bool):
    """
    Get information about a specific surah/chapter.
    
    Examples:
        qal surah 3          # Show surah info
        qal surah 3 --count  # Show verse count
        qal surah 3 --list   # List all verses in the surah
    """
    try:
        surah = get_surah(surah_number)
        
        if count:
            click.echo(f"Surah {surah_number} has {surah.get_verse_count()} verses")
        elif list:
            click.echo(f"Surah {surah_number} - All Verses:")
            click.echo("=" * 60)
            for verse in surah.get_all_verses():
                display_verse(verse, compact=True)
        else:
            click.echo(f"Surah {surah_number}")
            click.echo(f"Total verses: {surah.get_verse_count()}")
            click.echo(f"Has Basmala: {'Yes' if surah.has_basmala() else 'No'}")
            
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command(name="search", help="Search for verses containing a specific text query")
@click.argument("query")
@click.option("--normalized/--original", default=True, help="Search in normalized or original text")
@click.option("--limit", "-l", type=int, help="Limit number of results")
@style_option
@click.pass_context
def search_text_cmd(ctx,query: str, normalized: bool, limit: Optional[int]):
    """
    Search for verses containing the query text (exact substring matching).
    
    Examples:
        qal search "الله"
        qal search "بسم الله" --limit 5
        qal search "الرحمن" --original
    """
    try:
        results = search_text(query, normalized=normalized)
        
        if not results:
            click.echo(f"No verses found containing '{query}'")
            return
        
        total = len(results)
        display_count = min(limit, total) if limit else total
        
        click.echo(f"Found {total} verse(s) containing '{query}'")
        click.echo("=" * 60)
        
        for i, verse in enumerate(results[:display_count], 1):
            click.echo(f"\n[{i}/{display_count}] ", nl=False)
            display_verse(verse, compact=True)
        
        if limit and total > limit:
            click.echo(f"\n... and {total - limit} more results")
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command(name="fuzzy", help="Perform fuzzy search with partial text matching")
@click.argument("query")
@click.option("--threshold", "-t", type=float, default=0.7, help="Minimum similarity score (0.0-1.0)")
@click.option("--normalized/--original", default=True, help="Search in normalized or original text")
@click.option("--limit", "-l", type=int, help="Limit number of results")
@style_option
@click.pass_context
def fuzzy_search_cmd(ctx,query: str, threshold: float, normalized: bool, limit: Optional[int]):
    """
    Perform fuzzy search with partial text matching.
    
    Examples:
        qal fuzzy "كذلك يجتبيك ربك ويعلمك"
        qal fuzzy "فبأي الاء ربكما تكذبان" --threshold 0.8
        qal fuzzy "بسم الله" --limit 10
    """
    try:
        if threshold < 0.0 or threshold > 1.0:
            click.echo("Error: Threshold must be between 0.0 and 1.0", err=True)
            sys.exit(1)
        
        results = fuzzy_search(query, threshold=threshold, normalized=normalized, max_results=limit)
        
        if not results:
            click.echo(f"No verses found matching '{query}' with threshold {threshold}")
            return
        
        total = len(results)
        click.echo(f"Found {total} fuzzy match(es) for '{query}' (threshold: {threshold})")
        click.echo("=" * 60)
        
        for i, result in enumerate(results, 1):
            click.echo(f"\n[{i}/{total}] Similarity: {result.similarity:.3f} | Words: {result.start_word}-{result.end_word}")
            click.echo(f"Matched text: {result.matched_text}")
            display_verse(result.verse, compact=True)
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command(name="list-verses", help="List all verses in a specific surah")
@click.argument("surah_number", type=int)
@style_option
@click.pass_context
def get_surah_verses_cmd(ctx, surah_number: int):
    """
    Get all verses for a specific surah.
    
    Examples:
        qal list-verses 1
        qal list-verses 114
    """
    try:
        verses = get_surah_verses(surah_number)
        
        click.echo(f"Surah {surah_number} - All {len(verses)} verse(s):")
        click.echo("=" * 60)
        
        for verse in verses:
            display_verse(verse, compact=True)
            
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command(name="sliding-window", help="Search for text that may span multiple ayahs using a sliding window approach")
@click.argument("query")
@click.option("--threshold", "-t", type=float, default=80.0, help="Minimum similarity score (0.0-100.0)")
@click.option("--normalized/--original", default=True, help="Search in normalized or original text")
@click.option("--limit", "-l", type=int, help="Limit number of results")
@style_option
@click.pass_context
def sliding_window_search_cmd(ctx, query: str, threshold: float, normalized: bool, limit: Optional[int]):
    """
    Search for text that may span multiple ayahs using a sliding window approach.
    
    This command is useful for finding longer passages or quotes that cross ayah
    or even surah boundaries. It uses vectorized fuzzy matching for efficient searching.
    
    Examples:
        qal sliding-window "الرحمن علم القران خلق الانسان علمه البيان"
        qal sliding-window "بسم الله الرحمن الرحيم الم ذلك الكتاب" --threshold 85
        qal sliding-window "فبأي الاء ربكما تكذبان" --limit 5
    """
    try:
        if threshold < 0.0 or threshold > 100.0:
            click.echo("Error: Threshold must be between 0.0 and 100.0", err=True)
            sys.exit(1)
        
        results = search_sliding_window(query, threshold=threshold, normalized=normalized, max_results=limit)
        
        if not results:
            click.echo(f"No matches found for '{query}' with threshold {threshold}")
            return
        
        total = len(results)
        click.echo(f"Found {total} match(es) for '{query}' (threshold: {threshold})")
        click.echo("=" * 60)
        
        for i, match in enumerate(results, 1):
            click.echo(f"\n[{i}/{total}] Similarity: {match.similarity:.1f} | Reference: {match.get_reference()}")
            click.echo(f"Matched text: {match.matched_text}")
            click.echo(f"Verses involved: {len(match.verses)}")
            
            # Display each verse in the match
            for verse in match.verses:
                click.echo(f"  - Surah {verse.surah_number}:{verse.ayah_number}")
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command(name="smart-search", help="Intelligent search that tries exact, fuzzy, and sliding window methods")
@click.argument("query")
@click.option("--fuzzy-threshold", "-f", type=float, default=0.7, help="Fuzzy search threshold (0.0-1.0)")
@click.option("--sliding-threshold", "-s", type=float, default=80.0, help="Sliding window threshold (0.0-100.0)")
@click.option("--normalized/--original", default=True, help="Search in normalized or original text")
@click.option("--limit", "-l", type=int, help="Limit number of results")
@style_option
@click.pass_context
def smart_search_cmd(ctx, query: str, fuzzy_threshold: float, sliding_threshold: float, 
                     normalized: bool, limit: Optional[int]):
    """
    Intelligent search that automatically tries multiple search methods.
    
    This command tries different search methods in order of precision:
    1. Exact text search (fastest, most precise)
    2. Fuzzy search (moderate speed, handles variations)
    3. Sliding window search (slower, handles multi-ayah matches)
    
    The first method that returns results will be used, making this the most
    convenient search command for general use.
    
    Examples:
        qal smart-search "الرحمن الرحيم"
        qal smart-search "الرحمن علم القران خلق الانسان" --limit 5
        qal smart-search "فبأي الاء" --fuzzy-threshold 0.8
    """
    try:
        if fuzzy_threshold < 0.0 or fuzzy_threshold > 1.0:
            click.echo("Error: Fuzzy threshold must be between 0.0 and 1.0", err=True)
            sys.exit(1)
        
        if sliding_threshold < 0.0 or sliding_threshold > 100.0:
            click.echo("Error: Sliding threshold must be between 0.0 and 100.0", err=True)
            sys.exit(1)
        
        result = smart_search(
            query, 
            threshold=fuzzy_threshold,
            sliding_threshold=sliding_threshold,
            normalized=normalized, 
            max_results=limit
        )
        
        if result['count'] == 0:
            click.echo(f"No results found for '{query}' using any search method")
            return
        
        # Display header with method used
        method_names = {
            'exact': 'Exact Text Search',
            'fuzzy': 'Fuzzy Search',
            'sliding_window': 'Sliding Window Search'
        }
        method_name = method_names.get(result['method'], result['method'])
        
        click.echo(f"Found {result['count']} result(s) using {method_name}")
        click.echo("=" * 60)
        
        # Display results based on method type
        if result['method'] == 'exact':
            for i, verse in enumerate(result['results'], 1):
                click.echo(f"\n[{i}/{result['count']}] ", nl=False)
                display_verse(verse, compact=True)
                
        elif result['method'] == 'fuzzy':
            for i, fuzzy_result in enumerate(result['results'], 1):
                click.echo(f"\n[{i}/{result['count']}] Similarity: {fuzzy_result.similarity:.3f} | Words: {fuzzy_result.start_word}-{fuzzy_result.end_word}")
                click.echo(f"Matched text: {fuzzy_result.matched_text}")
                display_verse(fuzzy_result.verse, compact=True)
                
        elif result['method'] == 'sliding_window':
            for i, match in enumerate(result['results'], 1):
                click.echo(f"\n[{i}/{result['count']}] Similarity: {match.similarity:.1f} | Reference: {match.get_reference()}")
                click.echo(f"Matched text: {match.matched_text}")
                click.echo(f"Verses involved: {len(match.verses)}")
                for verse in match.verses:
                    click.echo(f"  - Surah {verse.surah_number}:{verse.ayah_number}")
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command(name="stats", help="Show database statistics")
@style_option
@click.pass_context
def show_stats(ctx):
    """
    Show database statistics.
    
    Examples:
        qal stats
    """
    try:
        db = get_quran_database()
        click.echo("Quran Database Statistics")
        click.echo("=" * 60)
        click.echo(f"Quran Style Version: {db.corpus_style.name}, file: {db.corpus_style.value}")
        click.echo(f"Total surahs: {len(db.surahs)}")
        click.echo(f"Total verses: {db.total_verses}")
        click.echo(f"Source: Tanzil.net")
        click.echo(f"Text: Arabic only (no translations)")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command(name="serve", help="Start the REST API server")
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
@click.option("--port", "-p", type=int, default=8000, help="Port to bind to (default: 8000)")
@click.option("--reload", "-r", is_flag=True, help="Enable auto-reload for development")
@style_option
@click.pass_context
def serve_api(ctx, host: str, port: int, reload: bool):
    """
    Start the REST API server.
    
    The API provides RESTful endpoints for all package functionalities including
    verse lookup, text search, fuzzy search, and database statistics.
    
    Examples:
        qal serve                          # Start server on default host:port
        qal serve --port 8080              # Start server on custom port
        qal serve --host 0.0.0.0 --port 80 # Make server publicly accessible
        qal serve --reload                 # Start with auto-reload for development
    """
    try:
        click.echo("Starting Quran Ayah Lookup API Server...")
        click.echo("=" * 60)
        click.echo(f"Host: {host}")
        click.echo(f"Port: {port}")
        click.echo(f"Reload: {'Enabled' if reload else 'Disabled'}")
        click.echo("=" * 60)
        click.echo(f"API Documentation: http://{host}:{port}/docs")
        click.echo(f"API Root: http://{host}:{port}/")
        click.echo("=" * 60)
        click.echo("Press Ctrl+C to stop the server")
        click.echo()
        
        # Import and run the API server
        try:
            from .api import run_server
            run_server(host=host, port=port, reload=reload)
        except ImportError as e:
            click.echo(f"Error: Failed to import API module. Make sure FastAPI and uvicorn are installed.", err=True)
            click.echo(f"Install with: pip install fastapi uvicorn[standard]", err=True)
            click.echo(f"Details: {e}", err=True)
            sys.exit(1)
            
    except KeyboardInterrupt:
        click.echo("\n\nServer stopped.")
    except Exception as e:
        click.echo(f"Error starting server: {e}", err=True)
        sys.exit(1)


def repl_mode():
    """Interactive REPL mode for the CLI."""
    click.echo("=" * 60)
    click.echo("Quran Ayah Lookup - Interactive REPL Mode")
    click.echo("=" * 60)
    click.echo("Commands:")
    click.echo("  verse <surah> <ayah>       - Get a specific verse")
    click.echo("  surah <number>             - Get surah information")
    click.echo("  search <query>             - Search for text")
    click.echo("  fuzzy <query>              - Fuzzy search")
    click.echo("  stats                      - Show database stats")
    click.echo("  help                       - Show this help")
    click.echo("  exit / quit / Ctrl+C       - Exit REPL")
    click.echo("=" * 60)
    click.echo()
    
    while True:
        try:
            try:
                user_input = click.prompt("qal>", type=str, default="", show_default=False)
            except (KeyboardInterrupt, EOFError):
                click.echo("\nGoodbye!")
                break
            
            user_input = user_input.strip()
            
            if not user_input:
                continue
            
            # Parse the input
            parts = user_input.split()
            command = parts[0].lower()
            
            if command in ["exit", "quit"]:
                click.echo("Goodbye!")
                break
            elif command == "help":
                repl_mode()
                break
            elif command == "verse" and len(parts) >= 3:
                try:
                    surah = int(parts[1])
                    ayah = int(parts[2])
                    verse = get_verse(surah, ayah)
                    display_verse(verse)
                except ValueError as e:
                    click.echo(f"Error: {e}")
            elif command == "surah" and len(parts) >= 2:
                try:
                    surah_number = int(parts[1])
                    surah = get_surah(surah_number)
                    click.echo(f"Surah {surah_number}")
                    click.echo(f"Total verses: {surah.get_verse_count()}")
                    click.echo(f"Has Basmala: {'Yes' if surah.has_basmala() else 'No'}")
                except ValueError as e:
                    click.echo(f"Error: {e}")
            elif command == "search" and len(parts) >= 2:
                query = " ".join(parts[1:])
                results = search_text(query)
                click.echo(f"Found {len(results)} verse(s)")
                for i, verse in enumerate(results[:5], 1):
                    click.echo(f"\n[{i}] ", nl=False)
                    display_verse(verse, compact=True)
                if len(results) > 5:
                    click.echo(f"\n... and {len(results) - 5} more")
            elif command == "fuzzy" and len(parts) >= 2:
                query = " ".join(parts[1:])
                results = fuzzy_search(query)
                click.echo(f"Found {len(results)} fuzzy match(es)")
                for i, result in enumerate(results[:5], 1):
                    click.echo(f"\n[{i}] Similarity: {result.similarity:.3f}")
                    display_verse(result.verse, compact=True)
                if len(results) > 5:
                    click.echo(f"\n... and {len(results) - 5} more")
            elif command == "stats":
                db = get_quran_database()
                click.echo(f"Total surahs: {len(db.surahs)}")
                click.echo(f"Total verses: {db.total_verses}")
            else:
                click.echo(f"Unknown command or invalid arguments. Type 'help' for available commands.")
                
        except Exception as e:
            click.echo(f"Error: {e}")


def display_verse(verse, normalized=False, original=False, compact=False):
    """Helper function to display a verse with formatting."""
    verse_type = "Basmala" if verse.is_basmalah else "Ayah"
    
    if compact:
        click.echo(f"{verse_type} {verse.surah_number}:{verse.ayah_number} - {verse.text}")
    else:
        click.echo(f"\n{verse_type} {verse.surah_number}:{verse.ayah_number}")
        click.echo("-" * 40)
        
        if original:
            click.echo(f"Original: {verse.text}")
        elif normalized:
            click.echo(f"Normalized: {verse.text_normalized}")
        else:
            click.echo(f"Original: {verse.text}")
            click.echo(f"Normalized: {verse.text_normalized}")


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
