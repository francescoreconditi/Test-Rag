"""
Customizable Dashboard Manager with Drag-and-Drop Support
==========================================================

Provides a flexible dashboard system with draggable widgets and persistent layouts.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
import json
from pathlib import Path
from typing import Any, Callable, Optional
import uuid

import streamlit as st


class WidgetType(Enum):
    """Available widget types."""
    METRIC = "metric"
    CHART = "chart"
    TABLE = "table"
    TEXT = "text"
    CUSTOM = "custom"
    KPI = "kpi"
    TIMELINE = "timeline"
    MAP = "map"

class WidgetSize(Enum):
    """Widget size presets."""
    SMALL = (1, 1)    # 1x1 grid units
    MEDIUM = (2, 1)   # 2x1 grid units
    LARGE = (2, 2)    # 2x2 grid units
    WIDE = (4, 1)     # 4x1 grid units
    TALL = (1, 2)     # 1x2 grid units
    FULL = (4, 2)     # 4x2 grid units

@dataclass
class WidgetConfig:
    """Configuration for a dashboard widget."""
    id: str
    type: WidgetType
    title: str
    position: dict[str, int]  # {'x': 0, 'y': 0}
    size: dict[str, int]      # {'width': 2, 'height': 1}
    content: dict[str, Any] = field(default_factory=dict)
    refresh_interval: Optional[int] = None  # seconds
    visible: bool = True
    locked: bool = False
    custom_style: dict[str, str] = field(default_factory=dict)

@dataclass
class DashboardLayout:
    """Dashboard layout configuration."""
    id: str
    name: str
    description: str
    widgets: list[WidgetConfig]
    grid_columns: int = 4
    grid_rows: int = 6
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_default: bool = False
    tags: list[str] = field(default_factory=list)

class DashboardManager:
    """Manages customizable dashboards with drag-and-drop functionality."""

    def __init__(self, tenant_id: Optional[str] = None):
        """Initialize dashboard manager."""
        self.tenant_id = tenant_id or "default"
        self.layouts_dir = Path(f"data/dashboards/{self.tenant_id}")
        self.layouts_dir.mkdir(parents=True, exist_ok=True)
        self.current_layout: Optional[DashboardLayout] = None

    def create_widget(self,
                     widget_type: WidgetType,
                     title: str,
                     position: tuple = (0, 0),
                     size: WidgetSize = WidgetSize.MEDIUM,
                     content: dict[str, Any] = None) -> WidgetConfig:
        """Create a new widget configuration."""
        widget_id = str(uuid.uuid4())[:8]

        return WidgetConfig(
            id=widget_id,
            type=widget_type,
            title=title,
            position={'x': position[0], 'y': position[1]},
            size={'width': size.value[0], 'height': size.value[1]},
            content=content or {}
        )

    def create_default_layout(self) -> DashboardLayout:
        """Create a default dashboard layout."""
        widgets = [
            # Row 1: KPIs
            self.create_widget(
                WidgetType.KPI,
                "Total Documents",
                position=(0, 0),
                size=WidgetSize.SMALL,
                content={'metric': 'total_documents', 'icon': '📄'}
            ),
            self.create_widget(
                WidgetType.KPI,
                "Queries Today",
                position=(1, 0),
                size=WidgetSize.SMALL,
                content={'metric': 'queries_today', 'icon': '🔍'}
            ),
            self.create_widget(
                WidgetType.KPI,
                "Avg Response Time",
                position=(2, 0),
                size=WidgetSize.SMALL,
                content={'metric': 'avg_response_time', 'icon': '⚡'}
            ),
            self.create_widget(
                WidgetType.KPI,
                "Active Users",
                position=(3, 0),
                size=WidgetSize.SMALL,
                content={'metric': 'active_users', 'icon': '👥'}
            ),

            # Row 2-3: Charts
            self.create_widget(
                WidgetType.CHART,
                "Query Volume Trend",
                position=(0, 1),
                size=WidgetSize.LARGE,
                content={'chart_type': 'line', 'data_source': 'query_volume'}
            ),
            self.create_widget(
                WidgetType.CHART,
                "Document Categories",
                position=(2, 1),
                size=WidgetSize.LARGE,
                content={'chart_type': 'pie', 'data_source': 'doc_categories'}
            ),

            # Row 4: Timeline
            self.create_widget(
                WidgetType.TIMELINE,
                "Recent Activity",
                position=(0, 3),
                size=WidgetSize.WIDE,
                content={'limit': 10, 'show_details': True}
            ),

            # Row 5-6: Table
            self.create_widget(
                WidgetType.TABLE,
                "Top Queries",
                position=(0, 4),
                size=WidgetSize.FULL,
                content={'data_source': 'top_queries', 'rows': 10}
            )
        ]

        return DashboardLayout(
            id="default",
            name="Default Dashboard",
            description="Standard dashboard layout with key metrics",
            widgets=widgets,
            is_default=True,
            tags=["standard", "overview"]
        )

    def save_layout(self, layout: DashboardLayout):
        """Save dashboard layout to file."""
        layout.updated_at = datetime.now()
        layout_file = self.layouts_dir / f"{layout.id}.json"

        # Convert to dict for JSON serialization
        layout_dict = asdict(layout)
        # Convert datetime to ISO format
        layout_dict['created_at'] = layout.created_at.isoformat()
        layout_dict['updated_at'] = layout.updated_at.isoformat()
        # Convert enums to values
        for widget in layout_dict['widgets']:
            widget['type'] = widget['type'].value if isinstance(widget['type'], WidgetType) else widget['type']

        with open(layout_file, 'w') as f:
            json.dump(layout_dict, f, indent=2)

    def load_layout(self, layout_id: str) -> Optional[DashboardLayout]:
        """Load dashboard layout from file."""
        layout_file = self.layouts_dir / f"{layout_id}.json"

        if not layout_file.exists():
            if layout_id == "default":
                # Create and save default layout
                layout = self.create_default_layout()
                self.save_layout(layout)
                return layout
            return None

        with open(layout_file) as f:
            layout_dict = json.load(f)

        # Convert datetime strings back to datetime objects
        layout_dict['created_at'] = datetime.fromisoformat(layout_dict['created_at'])
        layout_dict['updated_at'] = datetime.fromisoformat(layout_dict['updated_at'])

        # Convert widget type strings back to enums
        for widget in layout_dict['widgets']:
            widget['type'] = WidgetType(widget['type'])

        # Create WidgetConfig objects
        layout_dict['widgets'] = [WidgetConfig(**w) for w in layout_dict['widgets']]

        return DashboardLayout(**layout_dict)

    def list_layouts(self) -> list[dict[str, Any]]:
        """List all available dashboard layouts."""
        layouts = []

        for layout_file in self.layouts_dir.glob("*.json"):
            try:
                with open(layout_file) as f:
                    layout_data = json.load(f)
                    layouts.append({
                        'id': layout_data['id'],
                        'name': layout_data['name'],
                        'description': layout_data['description'],
                        'updated_at': datetime.fromisoformat(layout_data['updated_at']),
                        'is_default': layout_data.get('is_default', False),
                        'tags': layout_data.get('tags', [])
                    })
            except:
                continue

        # Ensure default layout exists
        if not any(l['id'] == 'default' for l in layouts):
            default_layout = self.create_default_layout()
            self.save_layout(default_layout)
            layouts.append({
                'id': default_layout.id,
                'name': default_layout.name,
                'description': default_layout.description,
                'updated_at': default_layout.updated_at,
                'is_default': default_layout.is_default,
                'tags': default_layout.tags
            })

        return sorted(layouts, key=lambda x: x['updated_at'], reverse=True)

    def duplicate_layout(self, layout_id: str, new_name: str) -> Optional[DashboardLayout]:
        """Duplicate an existing layout."""
        original = self.load_layout(layout_id)
        if not original:
            return None

        new_layout = DashboardLayout(
            id=str(uuid.uuid4())[:8],
            name=new_name,
            description=f"Copy of {original.description}",
            widgets=original.widgets.copy(),
            grid_columns=original.grid_columns,
            grid_rows=original.grid_rows,
            is_default=False,
            tags=original.tags.copy()
        )

        self.save_layout(new_layout)
        return new_layout

    def delete_layout(self, layout_id: str) -> bool:
        """Delete a dashboard layout."""
        if layout_id == "default":
            return False  # Cannot delete default layout

        layout_file = self.layouts_dir / f"{layout_id}.json"
        if layout_file.exists():
            layout_file.unlink()
            return True
        return False

    def update_widget_position(self, layout_id: str, widget_id: str, new_position: dict[str, int]):
        """Update widget position in layout."""
        layout = self.load_layout(layout_id)
        if not layout:
            return False

        for widget in layout.widgets:
            if widget.id == widget_id:
                widget.position = new_position
                self.save_layout(layout)
                return True
        return False

    def update_widget_size(self, layout_id: str, widget_id: str, new_size: dict[str, int]):
        """Update widget size in layout."""
        layout = self.load_layout(layout_id)
        if not layout:
            return False

        for widget in layout.widgets:
            if widget.id == widget_id:
                widget.size = new_size
                self.save_layout(layout)
                return True
        return False

    def add_widget_to_layout(self, layout_id: str, widget: WidgetConfig):
        """Add a new widget to layout."""
        layout = self.load_layout(layout_id)
        if not layout:
            return False

        layout.widgets.append(widget)
        self.save_layout(layout)
        return True

    def remove_widget_from_layout(self, layout_id: str, widget_id: str):
        """Remove a widget from layout."""
        layout = self.load_layout(layout_id)
        if not layout:
            return False

        layout.widgets = [w for w in layout.widgets if w.id != widget_id]
        self.save_layout(layout)
        return True

    def render_dashboard(self, layout_id: str, data_provider: Optional[Callable] = None):
        """Render dashboard with specified layout."""
        layout = self.load_layout(layout_id)
        if not layout:
            st.error(f"Layout {layout_id} not found")
            return

        self.current_layout = layout

        # Add drag-and-drop JavaScript/CSS
        self._inject_dragdrop_support()

        # Create grid container
        st.markdown(f"""
        <div class="dashboard-grid" data-layout-id="{layout_id}"
             style="display: grid; grid-template-columns: repeat({layout.grid_columns}, 1fr);
                    grid-template-rows: repeat({layout.grid_rows}, 150px); gap: 1rem;">
        """, unsafe_allow_html=True)

        # Sort widgets by position for proper rendering
        sorted_widgets = sorted(layout.widgets, key=lambda w: (w.position['y'], w.position['x']))

        # Render each widget
        for widget in sorted_widgets:
            if widget.visible:
                self._render_widget(widget, data_provider)

        st.markdown("</div>", unsafe_allow_html=True)

    def _render_widget(self, widget: WidgetConfig, data_provider: Optional[Callable] = None):
        """Render individual widget."""
        # Calculate grid position
        grid_style = f"""
            grid-column: {widget.position['x'] + 1} / span {widget.size['width']};
            grid-row: {widget.position['y'] + 1} / span {widget.size['height']};
        """

        # Create widget container
        container = st.container()

        with container:
            # Add widget wrapper with drag handle
            st.markdown(f"""
            <div class="widget-container" data-widget-id="{widget.id}"
                 style="{grid_style}; position: relative;">
                <div class="widget-header">
                    <span class="widget-title">{widget.title}</span>
                    <span class="widget-handle" style="cursor: move;">⋮⋮</span>
                </div>
                <div class="widget-content">
            """, unsafe_allow_html=True)

            # Render widget content based on type
            if widget.type == WidgetType.KPI:
                self._render_kpi_widget(widget, data_provider)
            elif widget.type == WidgetType.CHART:
                self._render_chart_widget(widget, data_provider)
            elif widget.type == WidgetType.TABLE:
                self._render_table_widget(widget, data_provider)
            elif widget.type == WidgetType.TIMELINE:
                self._render_timeline_widget(widget, data_provider)
            elif widget.type == WidgetType.TEXT:
                self._render_text_widget(widget)
            elif widget.type == WidgetType.CUSTOM:
                self._render_custom_widget(widget, data_provider)

            st.markdown("</div></div>", unsafe_allow_html=True)

    def _render_kpi_widget(self, widget: WidgetConfig, data_provider: Optional[Callable]):
        """Render KPI metric widget."""
        if data_provider:
            data = data_provider(widget.content.get('metric'))
            value = data.get('value', 0)
            delta = data.get('delta', None)
        else:
            # Mock data for demo
            import random
            value = random.randint(100, 1000)
            delta = random.randint(-50, 50)

        icon = widget.content.get('icon', '📊')
        st.metric(
            label=f"{icon} {widget.title}",
            value=value,
            delta=delta
        )

    def _render_chart_widget(self, widget: WidgetConfig, data_provider: Optional[Callable]):
        """Render chart widget."""
        import numpy as np
        import pandas as pd
        import plotly.express as px

        if data_provider:
            data = data_provider(widget.content.get('data_source'))
            # Handle different data formats
            if isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                # If it's a dict with scalar values, create a simple dataframe
                if 'value' in data and 'delta' in data:
                    # This is likely KPI data, create mock chart data instead
                    dates = pd.date_range('2024-01-01', periods=30)
                    df = pd.DataFrame({
                        'date': dates,
                        'value': np.random.randn(30).cumsum() + 100
                    })
                else:
                    df = pd.DataFrame([data])
            else:
                # Fallback to mock data
                dates = pd.date_range('2024-01-01', periods=30)
                df = pd.DataFrame({
                    'date': dates,
                    'value': np.random.randn(30).cumsum() + 100
                })
        else:
            # Mock data for demo
            dates = pd.date_range('2024-01-01', periods=30)
            df = pd.DataFrame({
                'date': dates,
                'value': np.random.randn(30).cumsum() + 100
            })

        chart_type = widget.content.get('chart_type', 'line')

        if chart_type == 'line':
            fig = px.line(df, x='date', y='value', title=None)
        elif chart_type == 'bar':
            fig = px.bar(df, x='date', y='value', title=None)
        elif chart_type == 'pie':
            # Mock pie chart data
            pie_data = pd.DataFrame({
                'category': ['A', 'B', 'C', 'D'],
                'value': [30, 25, 20, 25]
            })
            fig = px.pie(pie_data, values='value', names='category', title=None)
        else:
            fig = px.scatter(df, x='date', y='value', title=None)

        fig.update_layout(
            margin={"l": 0, "r": 0, "t": 0, "b": 0},
            height=widget.size['height'] * 140,
            showlegend=False
        )

        st.plotly_chart(fig, use_container_width=True)

    def _render_table_widget(self, widget: WidgetConfig, data_provider: Optional[Callable]):
        """Render table widget."""
        import pandas as pd

        if data_provider:
            data = data_provider(widget.content.get('data_source'))
            df = pd.DataFrame(data)
        else:
            # Mock data for demo
            df = pd.DataFrame({
                'Query': ['Revenue 2023', 'Profit margin', 'Customer growth', 'Market share'],
                'Count': [145, 89, 67, 45],
                'Avg Time': ['0.8s', '1.2s', '0.5s', '0.9s'],
                'Success Rate': ['98%', '95%', '99%', '97%']
            })

        rows = widget.content.get('rows', 5)
        st.dataframe(df.head(rows), use_container_width=True, hide_index=True)

    def _render_timeline_widget(self, widget: WidgetConfig, data_provider: Optional[Callable]):
        """Render timeline widget."""

        if data_provider:
            events = data_provider('timeline_events')
        else:
            # Mock timeline data
            events = [
                {'time': '2 min ago', 'event': 'Document uploaded', 'user': 'admin@demo.com'},
                {'time': '15 min ago', 'event': 'Query executed', 'user': 'user1@demo.com'},
                {'time': '1 hour ago', 'event': 'Index rebuilt', 'user': 'system'},
                {'time': '3 hours ago', 'event': 'User login', 'user': 'admin@demo.com'},
            ]

        for event in events[:widget.content.get('limit', 5)]:
            st.markdown(f"**{event['time']}** - {event['event']} ({event['user']})")

    def _render_text_widget(self, widget: WidgetConfig):
        """Render text widget."""
        text = widget.content.get('text', 'No content')
        st.markdown(text)

    def _render_custom_widget(self, widget: WidgetConfig, data_provider: Optional[Callable]):
        """Render custom widget."""
        if data_provider:
            # Let data provider handle custom rendering
            data_provider(f"custom_{widget.id}", widget)
        else:
            st.info("Custom widget placeholder")

    def _inject_dragdrop_support(self):
        """Inject JavaScript for drag-and-drop support."""
        st.markdown("""
        <style>
            .dashboard-grid {
                position: relative;
                min-height: 600px;
            }

            .widget-container {
                background: var(--surface-color);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 1rem;
                transition: all 0.3s ease;
                overflow: hidden;
            }

            .widget-container.dragging {
                opacity: 0.5;
                transform: scale(0.95);
                cursor: move;
            }

            .widget-container.drag-over {
                border: 2px dashed var(--primary-color);
                background: var(--primary-light);
            }

            .widget-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 0.5rem;
                padding-bottom: 0.5rem;
                border-bottom: 1px solid var(--divider-color);
            }

            .widget-title {
                font-weight: bold;
                color: var(--text-primary);
            }

            .widget-handle {
                cursor: move;
                color: var(--text-secondary);
                user-select: none;
            }

            .widget-handle:hover {
                color: var(--primary-color);
            }

            .widget-content {
                height: calc(100% - 3rem);
                overflow: auto;
            }

            .resize-handle {
                position: absolute;
                bottom: 0;
                right: 0;
                width: 20px;
                height: 20px;
                cursor: nwse-resize;
                opacity: 0.3;
            }

            .resize-handle:hover {
                opacity: 0.6;
            }

            .resize-handle::before {
                content: '◢';
                position: absolute;
                bottom: 2px;
                right: 2px;
                color: var(--text-secondary);
            }
        </style>

        <script>
        // Dashboard drag-and-drop functionality
        (function() {
            let draggedElement = null;
            let draggedWidget = null;
            let originalPosition = null;

            // Initialize drag-and-drop for widgets
            function initDragDrop() {
                const widgets = document.querySelectorAll('.widget-container');
                const grid = document.querySelector('.dashboard-grid');

                if (!grid) return;

                widgets.forEach(widget => {
                    const handle = widget.querySelector('.widget-handle');
                    if (!handle) return;

                    // Make widget draggable via handle
                    handle.addEventListener('mousedown', startDrag);
                    widget.addEventListener('dragstart', handleDragStart);
                    widget.addEventListener('dragend', handleDragEnd);
                    widget.addEventListener('dragover', handleDragOver);
                    widget.addEventListener('drop', handleDrop);
                    widget.addEventListener('dragenter', handleDragEnter);
                    widget.addEventListener('dragleave', handleDragLeave);

                    // Make widget draggable
                    widget.draggable = true;
                });
            }

            function startDrag(e) {
                const widget = e.target.closest('.widget-container');
                if (widget) {
                    draggedWidget = widget;
                }
            }

            function handleDragStart(e) {
                if (e.target !== draggedWidget) return;

                draggedElement = e.target;
                originalPosition = {
                    gridColumn: e.target.style.gridColumn,
                    gridRow: e.target.style.gridRow
                };

                e.target.classList.add('dragging');
                e.dataTransfer.effectAllowed = 'move';
                e.dataTransfer.setData('text/html', e.target.innerHTML);
            }

            function handleDragEnd(e) {
                e.target.classList.remove('dragging');

                // Clean up any drag-over classes
                document.querySelectorAll('.drag-over').forEach(el => {
                    el.classList.remove('drag-over');
                });

                // Save new position to backend
                if (draggedElement && originalPosition) {
                    const newPosition = {
                        gridColumn: draggedElement.style.gridColumn,
                        gridRow: draggedElement.style.gridRow
                    };

                    if (newPosition.gridColumn !== originalPosition.gridColumn ||
                        newPosition.gridRow !== originalPosition.gridRow) {
                        saveWidgetPosition(draggedElement.dataset.widgetId, newPosition);
                    }
                }

                draggedElement = null;
                draggedWidget = null;
                originalPosition = null;
            }

            function handleDragOver(e) {
                if (e.preventDefault) {
                    e.preventDefault();
                }
                e.dataTransfer.dropEffect = 'move';
                return false;
            }

            function handleDragEnter(e) {
                if (draggedElement && e.target !== draggedElement &&
                    e.target.classList.contains('widget-container')) {
                    e.target.classList.add('drag-over');
                }
            }

            function handleDragLeave(e) {
                if (e.target.classList.contains('widget-container')) {
                    e.target.classList.remove('drag-over');
                }
            }

            function handleDrop(e) {
                if (e.stopPropagation) {
                    e.stopPropagation();
                }

                if (draggedElement && e.target !== draggedElement &&
                    e.target.classList.contains('widget-container')) {
                    // Swap positions
                    const targetPosition = {
                        gridColumn: e.target.style.gridColumn,
                        gridRow: e.target.style.gridRow
                    };

                    e.target.style.gridColumn = draggedElement.style.gridColumn;
                    e.target.style.gridRow = draggedElement.style.gridRow;

                    draggedElement.style.gridColumn = targetPosition.gridColumn;
                    draggedElement.style.gridRow = targetPosition.gridRow;
                }

                return false;
            }

            function saveWidgetPosition(widgetId, position) {
                // Send position update to Streamlit
                // This would need to be implemented with Streamlit components
                console.log('Saving widget position:', widgetId, position);
            }

            // Initialize on load
            document.addEventListener('DOMContentLoaded', initDragDrop);

            // Re-initialize on Streamlit rerun
            const observer = new MutationObserver(() => {
                if (document.querySelector('.dashboard-grid')) {
                    initDragDrop();
                }
            });

            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        })();
        </script>
        """, unsafe_allow_html=True)
