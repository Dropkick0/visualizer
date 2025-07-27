#!/usr/bin/env python3
"""
OCR and Parsing Calibration Tools for Portrait Preview Webapp.

This module provides tools to calibrate and optimize OCR performance,
test parsing accuracy, and generate calibration reports.
"""

import os
import sys
import argparse
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, asdict
import csv
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import load_config
from app.ocr import FileMakerOCR
from app.parse import FileMakerParser
from app.errors import OCRError, ParsingError


@dataclass
class CalibrationResult:
    """Results from a calibration test."""
    screenshot_path: str
    ocr_confidence: float
    lines_detected: int
    words_detected: int
    items_parsed: int
    codes_extracted: int
    processing_time: float
    success: bool
    errors: List[str]


@dataclass
class OCRSettings:
    """OCR configuration settings for testing."""
    psm: int = 6
    oem: int = 3
    min_confidence: float = 50.0
    preprocessing: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.preprocessing is None:
            self.preprocessing = {
                'grayscale': True,
                'contrast_enhancement': True,
                'noise_removal': True,
                'scaling_factor': 2.0
            }


class OCRCalibrator:
    """OCR calibration and optimization tools."""
    
    def __init__(self, config_path: str = None):
        """Initialize the calibrator."""
        if config_path:
            self.config = load_config(config_path)
        else:
            self.config = load_config()
        
        self.results: List[CalibrationResult] = []
    
    def test_ocr_settings(self, 
                         screenshot_paths: List[Path],
                         settings_variants: List[OCRSettings]) -> Dict[str, List[CalibrationResult]]:
        """Test different OCR settings on a set of screenshots."""
        results = {}
        
        for i, settings in enumerate(settings_variants):
            print(f"Testing OCR settings variant {i + 1}/{len(settings_variants)}")
            variant_results = []
            
            for screenshot_path in screenshot_paths:
                result = self._test_single_screenshot(screenshot_path, settings)
                variant_results.append(result)
                
            results[f"variant_{i + 1}"] = variant_results
        
        return results
    
    def _test_single_screenshot(self, 
                               screenshot_path: Path, 
                               settings: OCRSettings) -> CalibrationResult:
        """Test OCR on a single screenshot with specific settings."""
        import time
        
        start_time = time.time()
        errors = []
        
        try:
            # Create temporary config with test settings
            test_config = self.config
            test_config.settings.OCR_PSM = settings.psm
            test_config.settings.OCR_OEM = settings.oem
            test_config.settings.OCR_MIN_CONFIDENCE = settings.min_confidence
            
            # Run OCR
            ocr_processor = FileMakerOCR(test_config)
            ocr_result = ocr_processor.process_screenshot(screenshot_path, screenshot_path.parent)
            
            # Run parsing
            parser = FileMakerParser(test_config.products)
            parsed_items = parser.parse_ocr_lines(ocr_result.lines)
            
            # Count codes
            total_codes = sum(len(item.codes) for item in parsed_items)
            
            processing_time = time.time() - start_time
            
            return CalibrationResult(
                screenshot_path=str(screenshot_path),
                ocr_confidence=ocr_result.confidence_avg,
                lines_detected=len(ocr_result.lines),
                words_detected=len(ocr_result.words),
                items_parsed=len(parsed_items),
                codes_extracted=total_codes,
                processing_time=processing_time,
                success=True,
                errors=[]
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            errors.append(str(e))
            
            return CalibrationResult(
                screenshot_path=str(screenshot_path),
                ocr_confidence=0.0,
                lines_detected=0,
                words_detected=0,
                items_parsed=0,
                codes_extracted=0,
                processing_time=processing_time,
                success=False,
                errors=errors
            )
    
    def generate_calibration_report(self, 
                                  results: Dict[str, List[CalibrationResult]],
                                  output_dir: Path) -> Path:
        """Generate a comprehensive calibration report."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate CSV report
        csv_path = output_dir / "calibration_results.csv"
        self._generate_csv_report(results, csv_path)
        
        # Generate visual report
        html_path = output_dir / "calibration_report.html"
        self._generate_html_report(results, html_path)
        
        # Generate plots
        plots_dir = output_dir / "plots"
        plots_dir.mkdir(exist_ok=True)
        self._generate_plots(results, plots_dir)
        
        print(f"📊 Calibration report generated: {html_path}")
        return html_path
    
    def _generate_csv_report(self, 
                           results: Dict[str, List[CalibrationResult]], 
                           csv_path: Path):
        """Generate CSV report of calibration results."""
        with open(csv_path, 'w', newline='') as csvfile:
            fieldnames = [
                'variant', 'screenshot', 'success', 'ocr_confidence', 
                'lines_detected', 'words_detected', 'items_parsed', 
                'codes_extracted', 'processing_time', 'errors'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for variant_name, variant_results in results.items():
                for result in variant_results:
                    writer.writerow({
                        'variant': variant_name,
                        'screenshot': Path(result.screenshot_path).name,
                        'success': result.success,
                        'ocr_confidence': result.ocr_confidence,
                        'lines_detected': result.lines_detected,
                        'words_detected': result.words_detected,
                        'items_parsed': result.items_parsed,
                        'codes_extracted': result.codes_extracted,
                        'processing_time': result.processing_time,
                        'errors': '; '.join(result.errors) if result.errors else ''
                    })
    
    def _generate_html_report(self, 
                            results: Dict[str, List[CalibrationResult]], 
                            html_path: Path):
        """Generate HTML calibration report."""
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>OCR Calibration Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .success { color: green; }
        .error { color: red; }
        .metric { background-color: #f9f9f9; padding: 10px; margin: 10px 0; }
        .plot { text-align: center; margin: 20px 0; }
    </style>
</head>
<body>
    <h1>🔧 OCR Calibration Report</h1>
    <p>Generated: """ + str(pd.Timestamp.now()) + """</p>
    
    <h2>📊 Summary Statistics</h2>
"""
        
        # Calculate summary statistics
        for variant_name, variant_results in results.items():
            successful_results = [r for r in variant_results if r.success]
            
            if successful_results:
                avg_confidence = np.mean([r.ocr_confidence for r in successful_results])
                avg_items = np.mean([r.items_parsed for r in successful_results])
                avg_time = np.mean([r.processing_time for r in successful_results])
                success_rate = len(successful_results) / len(variant_results) * 100
                
                html_content += f"""
    <div class="metric">
        <h3>{variant_name}</h3>
        <p><strong>Success Rate:</strong> {success_rate:.1f}%</p>
        <p><strong>Average OCR Confidence:</strong> {avg_confidence:.1f}</p>
        <p><strong>Average Items Parsed:</strong> {avg_items:.1f}</p>
        <p><strong>Average Processing Time:</strong> {avg_time:.2f}s</p>
    </div>
"""
        
        # Add detailed results table
        html_content += """
    <h2>📋 Detailed Results</h2>
    <table>
        <thead>
            <tr>
                <th>Variant</th>
                <th>Screenshot</th>
                <th>Status</th>
                <th>OCR Confidence</th>
                <th>Lines</th>
                <th>Items</th>
                <th>Codes</th>
                <th>Time (s)</th>
            </tr>
        </thead>
        <tbody>
"""
        
        for variant_name, variant_results in results.items():
            for result in variant_results:
                status_class = "success" if result.success else "error"
                status_text = "✅ Success" if result.success else "❌ Failed"
                
                html_content += f"""
            <tr>
                <td>{variant_name}</td>
                <td>{Path(result.screenshot_path).name}</td>
                <td class="{status_class}">{status_text}</td>
                <td>{result.ocr_confidence:.1f}</td>
                <td>{result.lines_detected}</td>
                <td>{result.items_parsed}</td>
                <td>{result.codes_extracted}</td>
                <td>{result.processing_time:.2f}</td>
            </tr>
"""
        
        html_content += """
        </tbody>
    </table>
    
    <h2>📈 Performance Plots</h2>
    <div class="plot">
        <img src="plots/confidence_comparison.png" alt="OCR Confidence Comparison">
    </div>
    <div class="plot">
        <img src="plots/processing_time_comparison.png" alt="Processing Time Comparison">
    </div>
    
</body>
</html>
"""
        
        with open(html_path, 'w') as f:
            f.write(html_content)
    
    def _generate_plots(self, 
                       results: Dict[str, List[CalibrationResult]], 
                       plots_dir: Path):
        """Generate visualization plots."""
        import pandas as pd
        
        # Prepare data
        plot_data = []
        for variant_name, variant_results in results.items():
            for result in variant_results:
                if result.success:
                    plot_data.append({
                        'variant': variant_name,
                        'confidence': result.ocr_confidence,
                        'items_parsed': result.items_parsed,
                        'processing_time': result.processing_time
                    })
        
        df = pd.DataFrame(plot_data)
        
        if df.empty:
            return
        
        # OCR Confidence comparison
        plt.figure(figsize=(10, 6))
        df.boxplot(column='confidence', by='variant', ax=plt.gca())
        plt.title('OCR Confidence by Variant')
        plt.ylabel('OCR Confidence (%)')
        plt.xlabel('Variant')
        plt.tight_layout()
        plt.savefig(plots_dir / 'confidence_comparison.png', dpi=150, bbox_inches='tight')
        plt.close()
        
        # Processing time comparison
        plt.figure(figsize=(10, 6))
        df.boxplot(column='processing_time', by='variant', ax=plt.gca())
        plt.title('Processing Time by Variant')
        plt.ylabel('Processing Time (seconds)')
        plt.xlabel('Variant')
        plt.tight_layout()
        plt.savefig(plots_dir / 'processing_time_comparison.png', dpi=150, bbox_inches='tight')
        plt.close()


class ParsingCalibrator:
    """Parsing accuracy calibration tools."""
    
    def __init__(self, config_path: str = None):
        """Initialize the parsing calibrator."""
        if config_path:
            self.config = load_config(config_path)
        else:
            self.config = load_config()
    
    def create_ground_truth_dataset(self, 
                                   screenshots_dir: Path, 
                                   output_path: Path):
        """Create ground truth dataset for parsing accuracy testing."""
        ground_truth = []
        
        for screenshot_path in screenshots_dir.glob("*.png"):
            print(f"Processing {screenshot_path.name}...")
            
            # Manual annotation interface
            gt_entry = {
                'screenshot': str(screenshot_path),
                'expected_items': []
            }
            
            print(f"Annotating {screenshot_path.name}")
            print("Enter order items (press Enter with empty line to finish):")
            
            while True:
                line = input("Order line: ").strip()
                if not line:
                    break
                
                # Parse manually entered line
                item = {
                    'text': line,
                    'quantity': int(input("Quantity: ")),
                    'product': input("Product: "),
                    'codes': input("Codes (comma-separated): ").split(',')
                }
                gt_entry['expected_items'].append(item)
            
            ground_truth.append(gt_entry)
        
        # Save ground truth
        with open(output_path, 'w') as f:
            json.dump(ground_truth, f, indent=2)
        
        print(f"Ground truth dataset saved to {output_path}")
    
    def test_parsing_accuracy(self, 
                            ground_truth_path: Path) -> Dict[str, Any]:
        """Test parsing accuracy against ground truth dataset."""
        with open(ground_truth_path) as f:
            ground_truth = json.load(f)
        
        parser = FileMakerParser(self.config.products)
        results = {
            'total_screenshots': len(ground_truth),
            'correct_item_count': 0,
            'total_items': 0,
            'correct_codes': 0,
            'total_codes': 0,
            'detailed_results': []
        }
        
        for gt_entry in ground_truth:
            screenshot_path = Path(gt_entry['screenshot'])
            expected_items = gt_entry['expected_items']
            
            # Mock OCR result (use manual annotation)
            mock_lines = [item['text'] for item in expected_items]
            parsed_items = parser.parse_ocr_lines(mock_lines)
            
            # Compare results
            item_accuracy = len(parsed_items) == len(expected_items)
            if item_accuracy:
                results['correct_item_count'] += 1
            
            results['total_items'] += len(expected_items)
            
            # Check code extraction
            for i, (parsed, expected) in enumerate(zip(parsed_items, expected_items)):
                expected_codes = [c.strip() for c in expected['codes'] if c.strip()]
                if parsed.codes == expected_codes:
                    results['correct_codes'] += 1
                results['total_codes'] += 1
            
            results['detailed_results'].append({
                'screenshot': screenshot_path.name,
                'expected_items': len(expected_items),
                'parsed_items': len(parsed_items),
                'item_accuracy': item_accuracy
            })
        
        # Calculate percentages
        results['item_accuracy'] = (results['correct_item_count'] / results['total_screenshots']) * 100
        results['code_accuracy'] = (results['correct_codes'] / results['total_codes']) * 100 if results['total_codes'] > 0 else 0
        
        return results


def create_sample_ocr_settings() -> List[OCRSettings]:
    """Create sample OCR settings for calibration testing."""
    return [
        # Conservative settings
        OCRSettings(psm=6, oem=3, min_confidence=70.0),
        
        # Aggressive settings
        OCRSettings(psm=6, oem=3, min_confidence=30.0),
        
        # Alternative PSM
        OCRSettings(psm=7, oem=3, min_confidence=50.0),
        
        # Different OEM
        OCRSettings(psm=6, oem=1, min_confidence=50.0),
        
        # Enhanced preprocessing
        OCRSettings(
            psm=6, oem=3, min_confidence=50.0,
            preprocessing={
                'grayscale': True,
                'contrast_enhancement': True,
                'noise_removal': True,
                'scaling_factor': 3.0  # Higher scaling
            }
        )
    ]


def main():
    """Main calibration tool function."""
    parser = argparse.ArgumentParser(
        description="OCR and Parsing Calibration Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python calibration.py --test-ocr screenshots/ --output results/
  python calibration.py --create-ground-truth screenshots/ --gt-file ground_truth.json
  python calibration.py --test-parsing ground_truth.json
        """
    )
    
    parser.add_argument('--test-ocr', type=Path,
                       help='Test OCR settings on screenshots directory')
    parser.add_argument('--create-ground-truth', type=Path,
                       help='Create ground truth dataset from screenshots')
    parser.add_argument('--test-parsing', type=Path,
                       help='Test parsing accuracy against ground truth file')
    parser.add_argument('--gt-file', type=Path, default='ground_truth.json',
                       help='Ground truth file path')
    parser.add_argument('--output', type=Path, default='calibration_results',
                       help='Output directory for results')
    parser.add_argument('--config', type=Path,
                       help='Configuration file path')
    
    args = parser.parse_args()
    
    if args.test_ocr:
        print("🔧 Testing OCR settings...")
        calibrator = OCRCalibrator(args.config)
        
        # Get screenshot files
        screenshot_paths = list(args.test_ocr.glob("*.png"))
        if not screenshot_paths:
            print("❌ No PNG screenshots found in directory")
            return 1
        
        # Test different settings
        settings_variants = create_sample_ocr_settings()
        results = calibrator.test_ocr_settings(screenshot_paths, settings_variants)
        
        # Generate report
        report_path = calibrator.generate_calibration_report(results, args.output)
        print(f"✅ OCR calibration complete: {report_path}")
        
    elif args.create_ground_truth:
        print("📝 Creating ground truth dataset...")
        calibrator = ParsingCalibrator(args.config)
        calibrator.create_ground_truth_dataset(args.create_ground_truth, args.gt_file)
        
    elif args.test_parsing:
        print("📊 Testing parsing accuracy...")
        calibrator = ParsingCalibrator(args.config)
        results = calibrator.test_parsing_accuracy(args.test_parsing)
        
        print(f"\n📈 Parsing Accuracy Results:")
        print(f"  Item Count Accuracy: {results['item_accuracy']:.1f}%")
        print(f"  Code Extraction Accuracy: {results['code_accuracy']:.1f}%")
        
        # Save detailed results
        with open(args.output / 'parsing_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
    else:
        parser.print_help()
        return 1
    
    return 0


if __name__ == '__main__':
    import pandas as pd
    exit_code = main()
    sys.exit(exit_code) 