#!/usr/bin/env python3
"""
Script to plot GPU die temperature vs HBM temperature from CSV files in a zip archive
or directly from a Notion database.

Notion credentials are read from environment variables NOTION_TOKEN and
NOTION_DATABASE_ID. They can be supplied via a `.env` file at the repo root
(gitignored — see .env.example) or exported in the shell. Requires python-dotenv:
    pip install python-dotenv
"""

import argparse
import zipfile
import os
import sys
import tempfile
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import requests
from typing import Optional, Dict, Any

from dotenv import load_dotenv

# Load .env from the repo root (or any parent directory) into os.environ.
load_dotenv()

DEFAULT_NOTION_API_KEY = os.environ.get("NOTION_TOKEN")
DEFAULT_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")


def find_csv_in_private_shared(extract_dir):
    """Find CSV files in the 'Private & Shared' subfolder."""
    csv_files = []
    for root, dirs, files in os.walk(extract_dir):
        # Skip macOS metadata directories
        if '__MACOSX' in root:
            continue
        if 'Private & Shared' in root:
            for file in files:
                # Skip macOS metadata files (files starting with '._')
                if file.endswith('.csv') and not file.startswith('._'):
                    csv_files.append(os.path.join(root, file))
    return csv_files


def get_property_value(prop: Dict[str, Any]) -> Any:
    """Extract value from a Notion property based on its type."""
    prop_type = prop.get('type')
    
    if prop_type == 'title':
        if prop['title']:
            return ''.join([text['plain_text'] for text in prop['title']])
        return ''
    elif prop_type == 'rich_text':
        if prop['rich_text']:
            return ''.join([text['plain_text'] for text in prop['rich_text']])
        return ''
    elif prop_type == 'number':
        return prop['number']
    elif prop_type == 'select':
        return prop['select']['name'] if prop['select'] else None
    elif prop_type == 'multi_select':
        return ', '.join([item['name'] for item in prop['multi_select']])
    elif prop_type == 'date':
        return prop['date']['start'] if prop['date'] else None
    elif prop_type == 'checkbox':
        return prop['checkbox']
    elif prop_type == 'url':
        return prop['url']
    elif prop_type == 'email':
        return prop['email']
    elif prop_type == 'phone_number':
        return prop['phone_number']
    else:
        return None


def fetch_notion_database(database_id: str, api_token: str, customer: Optional[str] = None, 
                         project: Optional[str] = None) -> pd.DataFrame:
    """
    Fetch data from a Notion database and convert it to a pandas DataFrame.
    
    Parameters:
    -----------
    database_id : str
        The ID of the Notion database
    api_token : str
        The Notion API integration token
    customer : str, optional
        Filter by customer name (uses 'Customer' select property)
    project : str, optional
        Filter by project name (uses 'Project' select property)
    
    Returns:
    --------
    pd.DataFrame
        DataFrame containing the database rows
    """
    filter_desc = []
    if customer:
        filter_desc.append(f"Customer={customer}")
    if project:
        filter_desc.append(f"Project={project}")
    
    if filter_desc:
        print(f"Connecting to Notion database: {database_id} (filtering: {', '.join(filter_desc)})")
    else:
        print(f"Connecting to Notion database: {database_id} (no filters)")
    
    # Set up headers for Notion API
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    
    base_url = "https://api.notion.com/v1"
    
    # Build filters
    filters = []
    if customer:
        filters.append({
            "property": "Customer",
            "select": {
                "equals": customer
            }
        })
    if project:
        filters.append({
            "property": "Project",
            "select": {
                "equals": project
            }
        })
    
    # Query the database using requests
    try:
        results = []
        has_more = True
        start_cursor = None
        
        while has_more:
            url = f"{base_url}/databases/{database_id}/query"
            payload = {}
            
            # Add filters if any
            if filters:
                if len(filters) == 1:
                    payload["filter"] = filters[0]
                else:
                    payload["filter"] = {
                        "and": filters
                    }
            
            if start_cursor:
                payload["start_cursor"] = start_cursor
            
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            results.extend(data.get('results', []))
            has_more = data.get('has_more', False)
            start_cursor = data.get('next_cursor')
        
        print(f"Retrieved {len(results)} rows from Notion database")
        
        # Convert to DataFrame
        data = []
        for page in results:
            row = {}
            properties = page.get('properties', {})
            
            for prop_name, prop_value in properties.items():
                row[prop_name] = get_property_value(prop_value)
            
            data.append(row)
        
        df = pd.DataFrame(data)
        print(f"Converted to DataFrame with {len(df)} rows and {len(df.columns)} columns")
        print(f"Columns: {df.columns.tolist()}")
        
        return df
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Notion: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
        raise
    except Exception as e:
        print(f"Error processing Notion data: {e}")
        raise


def plot_temperature_data(csv_file=None, df=None, output_name=None, dark_mode=False, exclude=None, reference=None, 
                         gpu_target=None, hbm_target=None, highlight=None,
                         xlim_min=None, ylim_min=None, reference_label=None, reference_marker=None):
    """
    Plot GPU die temperature vs HBM temperature.
    
    Parameters:
    -----------
    csv_file : str, optional
        Path to the CSV file (if reading from file)
    df : pd.DataFrame, optional
        DataFrame containing the data (if reading from Notion or other source)
    output_name : str, optional
        Custom output filename for the plot
    dark_mode : bool
        If True, use dark theme for slides with black background
    exclude : list
        List of data point names to exclude from plotting
    reference : str
        Name of the data point to highlight as reference
    reference_label : str
        Custom label for the reference point annotation (optional)
    reference_marker : str
        Custom marker for the reference point (optional, defaults to '*')
    gpu_target : float
        GPU target temperature for green shaded region
    hbm_target : float
        HBM target temperature for green shaded region
    highlight : list of tuples
        List of (name, label, marker) tuples for highlighting specific data points
    xlim_min : float
        Minimum value for x-axis (GPU temperature)
    ylim_min : float
        Minimum value for y-axis (HBM temperature)
    """
    # Read data from CSV file or use provided DataFrame
    if df is None:
        if csv_file is None:
            raise ValueError("Either csv_file or df must be provided")
        df = pd.read_csv(csv_file)
    elif csv_file is not None:
        print("Warning: Both csv_file and df provided. Using df.")
    
    # Print columns to help with debugging
    print(f"CSV columns: {df.columns.tolist()}")
    
    # Try to identify temperature columns
    # Common column names for GPU die temperature
    gpu_temp_cols = [col for col in df.columns if any(
        x in col.lower() for x in ['gpu', 'die', 'gpu temp', 'die temp', 'gpu die']
    )]
    
    # Common column names for HBM temperature
    hbm_temp_cols = [col for col in df.columns if 'hbm' in col.lower()]
    
    # Try to identify name column
    name_cols = [col for col in df.columns if any(
        x in col.lower() for x in ['name', 'id', 'label', 'point']
    )]
    
    # Try to identify pressure drop column
    dp_cols = [col for col in df.columns if 'dp' in col.lower() and 'mbar' in col.lower()]
    if not dp_cols:
        dp_cols = [col for col in df.columns if 'pressure' in col.lower() or 'dp' in col.lower()]
    
    # Try to identify flow rate column
    flow_cols = [col for col in df.columns if 'flow' in col.lower() and 'lpm' in col.lower()]
    if not flow_cols:
        flow_cols = [col for col in df.columns if 'flow' in col.lower()]
    
    if not gpu_temp_cols:
        print("Warning: Could not find GPU temperature column. Using first numeric column.")
        numeric_cols = df.select_dtypes(include=['number']).columns
        gpu_temp_col = numeric_cols[0] if len(numeric_cols) > 0 else df.columns[0]
    else:
        gpu_temp_col = gpu_temp_cols[0]
    
    if not hbm_temp_cols:
        print("Warning: Could not find HBM temperature column. Using second numeric column.")
        numeric_cols = df.select_dtypes(include=['number']).columns
        hbm_temp_col = numeric_cols[1] if len(numeric_cols) > 1 else df.columns[1]
    else:
        hbm_temp_col = hbm_temp_cols[0]
    
    name_col = name_cols[0] if name_cols else df.columns[0]
    
    # Check for pressure drop column
    dp_col = None
    has_pressure_data = False
    if dp_cols:
        dp_col = dp_cols[0]
        has_pressure_data = True
    
    # Check for flow rate column
    flow_col = None
    has_flow_data = False
    if flow_cols:
        flow_col = flow_cols[0]
        has_flow_data = True
    
    # Print column information
    info_str = f"Using columns - Name: {name_col}, GPU Temp: {gpu_temp_col}, HBM Temp: {hbm_temp_col}"
    if has_pressure_data:
        info_str += f", Pressure Drop: {dp_col}"
    if has_flow_data:
        info_str += f", Flow Rate: {flow_col}"
    print(info_str)
    
    if not has_pressure_data:
        print("Warning: Pressure drop column not found. Markers will not be color-coded by pressure.")
    if not has_flow_data:
        print("Warning: Flow rate column not found. All markers will be filled.")
    
    # Filter out excluded data points
    if exclude:
        df = df[~df[name_col].isin(exclude)]
        print(f"Excluded {len(exclude)} data points: {exclude}")
    
    # Use uniform marker size for all points (pressure drop will be represented by color)
    uniform_marker_size = 150
    
    # Set up the plot style
    if dark_mode:
        plt.style.use('dark_background')
        regular_color = 'white'
        ref_color = '#FF4444'  # Brighter red for dark background
    else:
        regular_color = '#1f77b4'  # Default matplotlib blue
        ref_color = 'red'
    
    # Convert 12cm to inches (1 inch = 2.54 cm)
    fig_size_inches = 12 / 2.54
    
    # Create figure with specified size
    # fig, ax = plt.subplots(figsize=(fig_size_inches, fig_size_inches))
    fig, ax = plt.subplots()
    
    # Add target temperature region if specified
    if gpu_target is not None and hbm_target is not None:
        # Get current axis limits or set reasonable defaults
        all_data = df[[gpu_temp_col, hbm_temp_col]].values
        if len(all_data) > 0:
            x_min = 0
            y_min = 0
            # Draw a rectangle from (0,0) to (gpu_target, hbm_target)
            from matplotlib.patches import Rectangle
            rect = Rectangle((x_min, y_min), gpu_target - x_min, hbm_target - y_min,
                           linewidth=0, edgecolor='none', facecolor='green', alpha=0.5,
                           label='Target zone')
            ax.add_patch(rect)
    
    # Separate reference point and highlighted points
    ref_data = None
    highlighted_names = []
    
    # Collect names to exclude from regular plotting
    if reference:
        highlighted_names.append(reference)
    
    if highlight:
        for name, label, marker in highlight:
            highlighted_names.append(name)
    
    # Create mask for regular data points (excluding reference and highlighted)
    if highlighted_names:
        regular_mask = ~df[name_col].isin(highlighted_names)
        df_plot = df[regular_mask]
    else:
        df_plot = df
    
    # Plot regular data points
    # Store scatter plot for colorbar
    scatter_plot = None
    
    # Calculate global pressure range for consistent coloring
    vmin, vmax = None, None
    if has_pressure_data and dp_col in df.columns:
        vmin = df[dp_col].min()
        vmax = df[dp_col].max()
        print(f"Pressure drop range: {vmin:.1f} - {vmax:.1f} mbar")
    
    # Separate by flow rate (> 10 LPM = empty markers)
    if has_flow_data and flow_col in df_plot.columns:
        df_low_flow = df_plot[df_plot[flow_col] <= 10]
        df_high_flow = df_plot[df_plot[flow_col] > 10]
        
        # Plot low flow rate points (filled)
        if not df_low_flow.empty:
            if has_pressure_data and dp_col in df_low_flow.columns:
                colors = df_low_flow[dp_col]
                scatter_plot = ax.scatter(df_low_flow[gpu_temp_col], df_low_flow[hbm_temp_col], 
                           c=colors, cmap='plasma', vmin=vmin, vmax=vmax, s=uniform_marker_size, alpha=0.7, 
                           label='Flow ≤ 10 LPM', edgecolors='black', linewidths=0.5)
            else:
                ax.scatter(df_low_flow[gpu_temp_col], df_low_flow[hbm_temp_col], 
                           c=regular_color, s=uniform_marker_size, alpha=0.7, label='Flow ≤ 10 LPM',
                           edgecolors='black', linewidths=0.5)
        
        # Plot high flow rate points (empty)
        if not df_high_flow.empty:
            if has_pressure_data and dp_col in df_high_flow.columns:
                colors = df_high_flow[dp_col]
                sc = ax.scatter(df_high_flow[gpu_temp_col], df_high_flow[hbm_temp_col], 
                           c=colors, cmap='plasma', vmin=vmin, vmax=vmax, s=uniform_marker_size, 
                           facecolors='none', edgecolors='black', linewidths=0.5, alpha=0.7, label='Flow > 10 LPM')
                if scatter_plot is None:
                    scatter_plot = sc
            else:
                ax.scatter(df_high_flow[gpu_temp_col], df_high_flow[hbm_temp_col], 
                           facecolors='none', edgecolors='black', s=uniform_marker_size, 
                           linewidths=0.5, alpha=0.7, label='Flow > 10 LPM')
    else:
        # No flow rate data, plot all as filled
        if has_pressure_data and dp_col in df_plot.columns:
            colors = df_plot[dp_col]
            scatter_plot = ax.scatter(df_plot[gpu_temp_col], df_plot[hbm_temp_col], 
                       c=colors, cmap='plasma', vmin=vmin, vmax=vmax, s=uniform_marker_size, alpha=0.7, 
                       label='Data points', edgecolors='black', linewidths=0.5)
        else:
            ax.scatter(df_plot[gpu_temp_col], df_plot[hbm_temp_col], 
                       c=regular_color, s=uniform_marker_size, alpha=0.7, label='Data points',
                       edgecolors='black', linewidths=0.5)
    
    # Plot reference point if specified
    if reference:
        ref_mask = df[name_col] == reference
        ref_data = df[ref_mask]
    
    if reference and ref_data is not None and not ref_data.empty:
        # Set default marker if not specified
        ref_marker = reference_marker if reference_marker else '*'
        
        # Check if high flow rate (> 10 LPM)
        is_high_flow = False
        if has_flow_data and flow_col in ref_data.columns:
            is_high_flow = ref_data[flow_col].values[0] > 10
        
        # Use custom marker to distinguish reference point
        if has_pressure_data and dp_col in ref_data.columns:
            ref_pressure = ref_data[dp_col].values[0]
            if is_high_flow:
                # Empty marker for high flow
                sc = ax.scatter(ref_data[gpu_temp_col], ref_data[hbm_temp_col],
                          c=[ref_pressure], cmap='plasma', vmin=vmin, vmax=vmax, s=uniform_marker_size, marker=ref_marker,
                          facecolors='none', edgecolors='black', linewidths=0.5, label='Reference', zorder=5)
            else:
                # Filled marker for low flow
                sc = ax.scatter(ref_data[gpu_temp_col], ref_data[hbm_temp_col],
                          c=[ref_pressure], cmap='plasma', vmin=vmin, vmax=vmax, s=uniform_marker_size, marker=ref_marker, 
                          edgecolors='black', linewidths=0.5, label='Reference', zorder=5)
            if scatter_plot is None:
                scatter_plot = sc
        else:
            # No pressure data, use reference color
            if is_high_flow:
                ax.scatter(ref_data[gpu_temp_col], ref_data[hbm_temp_col],
                          facecolors='none', edgecolors='black', s=uniform_marker_size, marker=ref_marker,
                          linewidths=0.5, label='Reference', zorder=5)
            else:
                ax.scatter(ref_data[gpu_temp_col], ref_data[hbm_temp_col],
                          c=ref_color, s=uniform_marker_size, marker=ref_marker, edgecolors='black',
                          linewidths=0.5, label='Reference', zorder=5)
        
        # Add annotation above the reference point
        ref_x = ref_data[gpu_temp_col].values[0]
        ref_y = ref_data[hbm_temp_col].values[0]
        annotation_text = reference_label if reference_label else 'Ref.'
        # Use consistent color for annotation
        annot_color = 'white' if dark_mode else 'black'
        ax.annotate(annotation_text, xy=(ref_x, ref_y), xytext=(0, 15),
                   textcoords='offset points', ha='center', va='bottom',
                   fontsize=9, color=annot_color,
                   arrowprops=dict(arrowstyle='-', color=annot_color, linewidth=0.5))
    elif reference:
        print(f"Warning: Reference point '{reference}' not found in data.")
    
    # Plot highlighted points if specified
    if highlight:
        # Define different label positions to avoid overlap
        # Format: (x_offset, y_offset, horizontal_alignment, vertical_alignment)
        label_positions = [
            (-15, 15, 'right', 'bottom'),   # Northwest
            (15, 15, 'left', 'bottom'),     # Northeast
            (-15, -15, 'right', 'top'),     # Southwest
            (15, -15, 'left', 'top'),       # Southeast
            (0, 20, 'center', 'bottom'),    # North
            (0, -20, 'center', 'top'),      # South
            (20, 0, 'left', 'center'),      # East
            (-20, 0, 'right', 'center'),    # West
        ]
        
        for idx, (name, label, marker) in enumerate(highlight):
            highlight_mask = df[name_col] == name
            highlight_data = df[highlight_mask]
            
            if not highlight_data.empty:
                # Check if high flow rate (> 10 LPM)
                is_high_flow = False
                if has_flow_data and flow_col in highlight_data.columns:
                    is_high_flow = highlight_data[flow_col].values[0] > 10
                
                # Plot the highlighted point with custom marker and pressure-based color
                if has_pressure_data and dp_col in highlight_data.columns:
                    hl_pressure = highlight_data[dp_col].values[0]
                    if is_high_flow:
                        # Empty marker for high flow
                        sc = ax.scatter(highlight_data[gpu_temp_col], highlight_data[hbm_temp_col],
                                  c=[hl_pressure], cmap='plasma', vmin=vmin, vmax=vmax, s=uniform_marker_size, marker=marker,
                                  facecolors='none', edgecolors='black', linewidths=0.5, zorder=6)
                    else:
                        # Filled marker for low flow
                        sc = ax.scatter(highlight_data[gpu_temp_col], highlight_data[hbm_temp_col],
                                  c=[hl_pressure], cmap='plasma', vmin=vmin, vmax=vmax, s=uniform_marker_size, marker=marker, 
                                  edgecolors='black', linewidths=0.5, zorder=6)
                    if scatter_plot is None:
                        scatter_plot = sc
                else:
                    # No pressure data, use gold color
                    highlight_color = 'gold'
                    if is_high_flow:
                        ax.scatter(highlight_data[gpu_temp_col], highlight_data[hbm_temp_col],
                                  facecolors='none', edgecolors='black', s=uniform_marker_size, marker=marker,
                                  linewidths=0.5, zorder=6)
                    else:
                        ax.scatter(highlight_data[gpu_temp_col], highlight_data[hbm_temp_col],
                                  c=highlight_color, s=uniform_marker_size, marker=marker, 
                                  edgecolors='black', linewidths=0.5, zorder=6)
                
                # Add annotation with position cycling to avoid overlap
                hl_x = highlight_data[gpu_temp_col].values[0]
                hl_y = highlight_data[hbm_temp_col].values[0]
                
                # Cycle through different positions
                pos_idx = idx % len(label_positions)
                x_offset, y_offset, h_align, v_align = label_positions[pos_idx]
                
                # Use consistent color for annotation
                annot_color = 'white' if dark_mode else 'black'
                ax.annotate(label, xy=(hl_x, hl_y), xytext=(x_offset, y_offset),
                           textcoords='offset points', ha=h_align, va=v_align,
                           fontsize=9, color=annot_color,
                           arrowprops=dict(arrowstyle='-', color=annot_color, linewidth=0.5))
            else:
                print(f"Warning: Highlighted point '{name}' not found in data.")
    
    # Add colorbar if pressure data is available
    if has_pressure_data and scatter_plot is not None:
        cbar = plt.colorbar(scatter_plot, ax=ax)
        cbar.set_label('Pressure Drop (mbar)', fontsize=12)
        cbar.ax.tick_params(labelsize=10)
    
    # Set labels
    ax.set_xlabel('GPU Die Temperature (°C)', fontsize=12)
    ax.set_ylabel('HBM Temperature (°C)', fontsize=12)

    # Set axis limits
    # If not specified but targets are provided, use target - 20 as default
    if xlim_min is not None:
        ax.set_xlim(left=xlim_min, right=100)
    elif gpu_target is not None:
        ax.set_xlim(left=gpu_target - 20, right=100)
    
    if ylim_min is not None:
        ax.set_ylim(bottom=ylim_min, top=85)
    elif hbm_target is not None:
        ax.set_ylim(bottom=hbm_target - 20, top=85)
    
    # Add target annotation if both targets are specified
    if gpu_target is not None and hbm_target is not None:
        # Calculate center position for target annotation
        xlims = ax.get_xlim()
        ylims = ax.get_ylim()
        target_x = (xlims[0] + gpu_target) / 2
        target_y = (ylims[0] + hbm_target) / 2
        
        ax.annotate('Target', xy=(target_x, target_y), 
                   color='w', fontsize=12, rotation=90,
                   ha='center', va='center')

    # Set inward ticks
    ax.tick_params(axis='both', direction='in', which='both', top=True, right=True)
    
    # Add grid for better readability
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Tight layout to use space efficiently
    plt.tight_layout()
    
    # Save the plot
    if output_name is None:
        if csv_file:
            output_name = Path(csv_file).stem + '_temperature_plot.png'
        else:
            output_name = 'notion_temperature_plot.png'
    
    plt.savefig(output_name, dpi=300, bbox_inches='tight')
    print(f"Plot saved as: {output_name}")
    
    # Close the plot to free memory
    plt.close()


def main():
    parser = argparse.ArgumentParser(
        description='Plot GPU die temperature vs HBM temperature from CSV files in a zip archive or directly from Notion database.'
    )
    
    # Create mutually exclusive group for data source
    source_group = parser.add_mutually_exclusive_group(required=False)
    source_group.add_argument('--zip-file', type=str, 
                             help='Path to the zip file containing CSV data')
    source_group.add_argument('--notion-database', type=str, nargs='?', const=DEFAULT_DATABASE_ID,
                             help='Notion database ID to fetch data from (default: $NOTION_DATABASE_ID env var / .env)')

    parser.add_argument('--notion-token', type=str,
                       help='Notion API integration token (default: $NOTION_TOKEN env var / .env)')
    parser.add_argument('--customer', type=str, default=None,
                       help='Filter Notion database by Customer (only with --notion-database)')
    parser.add_argument('--project', type=str, default=None,
                       help='Filter Notion database by Project (only with --notion-database)')
    parser.add_argument('--output', type=str, default=None,
                       help='Custom output filename for the plot (default: auto-generated based on source)')
    parser.add_argument('--dark-mode', action='store_true', 
                       help='Use dark theme for slides with black background')
    parser.add_argument('--exclude', nargs='*', default=[],
                       help='List of data point names to exclude from plotting')
    parser.add_argument('--reference', nargs='+', default=None,
                       help='Name of the data point to highlight as reference. Optional second argument for custom label. Optional third argument for custom marker (e.g., "s", "o", "^", "D").')
    parser.add_argument('--GPU-target', type=float, default=None,
                       help='GPU target temperature for green shaded region')
    parser.add_argument('--HBM-target', type=float, default=None,
                       help='HBM target temperature for green shaded region')
    parser.add_argument('--xlim-min', type=float, default=None,
                       help='Minimum value for x-axis (GPU temperature). If not specified, uses automatic scaling.')
    parser.add_argument('--ylim-min', type=float, default=None,
                       help='Minimum value for y-axis (HBM temperature). If not specified, uses automatic scaling.')
    parser.add_argument('--highlight', nargs=3, action='append', metavar=('NAME', 'LABEL', 'MARKER'),
                       help='Highlight a data point with custom marker. Provide triplet: Name Label Marker. Can be used multiple times.')
    
    args = parser.parse_args()
    
    # Parse reference argument
    reference_name = None
    reference_label = None
    reference_marker = None
    if args.reference:
        reference_name = args.reference[0]
        if len(args.reference) > 1:
            reference_label = args.reference[1]
        if len(args.reference) > 2:
            reference_marker = args.reference[2]
    
    # Parse highlight argument into list of tuples
    highlight_list = []
    if args.highlight:
        for triplet in args.highlight:
            name, label, marker = triplet
            highlight_list.append((name, label, marker))
        
        print(f"Highlighting {len(highlight_list)} data point(s):")
    
    # Determine data source and fetch data
    df_data = None
    
    # Default to Notion if no source specified
    if args.notion_database is not None or (not args.zip_file):
        # Use Notion as data source
        database_id = args.notion_database if args.notion_database else DEFAULT_DATABASE_ID
        if not database_id:
            print("Error: Notion database ID required. Provide via --notion-database or set NOTION_DATABASE_ID in .env / environment.")
            sys.exit(1)

        # Get token from args, environment, or .env (loaded at module import).
        notion_token = args.notion_token or DEFAULT_NOTION_API_KEY
        if not notion_token:
            print("Error: Notion API token required. Provide via --notion-token or set NOTION_TOKEN in .env / environment.")
            sys.exit(1)
        
        # Validate filters are only used with Notion
        if args.zip_file and (args.customer or args.project):
            print("Warning: --customer and --project filters are ignored when using --zip-file")
        
        try:
            df_data = fetch_notion_database(database_id, notion_token, 
                                          customer=args.customer, 
                                          project=args.project)
        except Exception as e:
            print(f"Error fetching data from Notion: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        # Plot the data from Notion
        try:
            plot_temperature_data(df=df_data,
                                output_name=args.output,
                                dark_mode=args.dark_mode,
                                exclude=args.exclude,
                                reference=reference_name,
                                reference_label=reference_label,
                                reference_marker=reference_marker,
                                gpu_target=getattr(args, 'GPU_target', None),
                                hbm_target=getattr(args, 'HBM_target', None),
                                highlight=highlight_list if highlight_list else None,
                                xlim_min=args.xlim_min,
                                ylim_min=args.ylim_min)
        except Exception as e:
            print(f"Error plotting data: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    elif args.zip_file:
        # Process zip file (original functionality)
        # Check if zip file exists
        if not os.path.exists(args.zip_file):
            print(f"Error: Zip file '{args.zip_file}' not found.")
            sys.exit(1)
        
        # Create a temporary directory for extraction
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"Extracting zip file: {args.zip_file}")
            
            # Extract the zip file
            try:
                with zipfile.ZipFile(args.zip_file, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
            except Exception as e:
                print(f"Error extracting zip file: {e}")
                sys.exit(1)
            
            # Check for nested zip files and extract them too
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith('.zip'):
                        nested_zip = os.path.join(root, file)
                        print(f"Found nested zip file: {file}")
                        try:
                            with zipfile.ZipFile(nested_zip, 'r') as zip_ref:
                                zip_ref.extractall(root)
                            print(f"Extracted nested zip: {file}")
                        except Exception as e:
                            print(f"Warning: Could not extract nested zip {file}: {e}")
            
            # Find CSV files in 'Private & Shared' subfolder
            csv_files = find_csv_in_private_shared(temp_dir)
            
            if not csv_files:
                print("Error: No CSV files found in 'Private & Shared' subfolder.")
                sys.exit(1)
            
            print(f"Found {len(csv_files)} CSV file(s):")
            for csv_file in csv_files:
                print(f"  - {csv_file}")
            
            # Use the first CSV file found
            csv_file = csv_files[0]
            print(f"\nProcessing: {csv_file}")
            
            # Plot the data
            try:
                plot_temperature_data(csv_file=csv_file,
                                    output_name=args.output,
                                    dark_mode=args.dark_mode,
                                    exclude=args.exclude,
                                    reference=reference_name,
                                    reference_label=reference_label,
                                    reference_marker=reference_marker,
                                    gpu_target=getattr(args, 'GPU_target', None),
                                    hbm_target=getattr(args, 'HBM_target', None),
                                    highlight=highlight_list if highlight_list else None,
                                    xlim_min=args.xlim_min,
                                    ylim_min=args.ylim_min)
            except Exception as e:
                print(f"Error plotting data: {e}")
                import traceback
                traceback.print_exc()
                sys.exit(1)


if __name__ == '__main__':
    main()