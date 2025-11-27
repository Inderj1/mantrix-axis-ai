/**
 * ExportMenu - Export dashboard as PNG, PDF, or CSV
 */
import React, { useState } from 'react';
import {
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  CircularProgress,
  Backdrop
} from '@mui/material';
import {
  Image as ImageIcon,
  PictureAsPdf as PdfIcon,
  TableChart as CsvIcon
} from '@mui/icons-material';
import html2canvas from 'html2canvas';
import { jsPDF } from 'jspdf';

const ExportMenu = ({ anchorEl, onClose, dashboardRef, dashboard }) => {
  const [isExporting, setIsExporting] = useState(false);

  // Export as PNG
  const exportAsPNG = async () => {
    if (!dashboardRef?.current) return;

    setIsExporting(true);
    try {
      const canvas = await html2canvas(dashboardRef.current, {
        scale: 2,
        useCORS: true,
        logging: false
      });

      const link = document.createElement('a');
      link.download = `${dashboard?.name || 'dashboard'}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    } catch (error) {
      console.error('Failed to export PNG:', error);
    } finally {
      setIsExporting(false);
      onClose();
    }
  };

  // Export as PDF
  const exportAsPDF = async () => {
    if (!dashboardRef?.current) return;

    setIsExporting(true);
    try {
      const canvas = await html2canvas(dashboardRef.current, {
        scale: 2,
        useCORS: true,
        logging: false
      });

      const imgData = canvas.toDataURL('image/png');
      const pdf = new jsPDF({
        orientation: 'landscape',
        unit: 'mm',
        format: 'a4'
      });

      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = pdf.internal.pageSize.getHeight();
      const imgWidth = canvas.width;
      const imgHeight = canvas.height;
      const ratio = Math.min(pdfWidth / imgWidth, pdfHeight / imgHeight);

      const imgX = (pdfWidth - imgWidth * ratio) / 2;
      const imgY = 10;

      pdf.addImage(imgData, 'PNG', imgX, imgY, imgWidth * ratio, imgHeight * ratio);
      pdf.save(`${dashboard?.name || 'dashboard'}.pdf`);
    } catch (error) {
      console.error('Failed to export PDF:', error);
    } finally {
      setIsExporting(false);
      onClose();
    }
  };

  // Export data as CSV
  const exportAsCSV = () => {
    if (!dashboard?.widgets) return;

    setIsExporting(true);
    try {
      // Collect all widget data
      // Note: In a real implementation, you'd get this from the widget data cache
      const widgets = dashboard.widgets.filter(w => w.type === 'chart' || w.type === 'table');

      if (widgets.length === 0) {
        alert('No data widgets to export');
        return;
      }

      // For now, just export the queries as a reference
      const csvContent = [
        ['Widget Title', 'Query', 'Chart Type'].join(','),
        ...widgets.map(w =>
          [
            `"${w.title || 'Untitled'}"`,
            `"${w.query || ''}"`,
            `"${w.chart_type || 'table'}"`
          ].join(',')
        )
      ].join('\n');

      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `${dashboard?.name || 'dashboard'}_config.csv`;
      link.click();
    } catch (error) {
      console.error('Failed to export CSV:', error);
    } finally {
      setIsExporting(false);
      onClose();
    }
  };

  return (
    <>
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={onClose}
      >
        <MenuItem onClick={exportAsPNG}>
          <ListItemIcon>
            <ImageIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Export as PNG</ListItemText>
        </MenuItem>

        <MenuItem onClick={exportAsPDF}>
          <ListItemIcon>
            <PdfIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Export as PDF</ListItemText>
        </MenuItem>

        <MenuItem onClick={exportAsCSV}>
          <ListItemIcon>
            <CsvIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Export Data as CSV</ListItemText>
        </MenuItem>
      </Menu>

      {/* Loading backdrop */}
      <Backdrop open={isExporting} sx={{ zIndex: 9999 }}>
        <CircularProgress color="inherit" />
      </Backdrop>
    </>
  );
};

export default ExportMenu;
