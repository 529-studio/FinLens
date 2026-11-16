/**
 * Unit tests for coordinate_math utility
 * Governed by 529 Engineering Standards
 */

import { describe, it, expect } from 'vitest';
import {
  scaleBoundingBox,
  sanitizeBoundingBox,
  isValidBoundingBox,
  calculateBoundingBoxCenter,
  formatConfidence,
} from '../coordinate_math';

describe('coordinate_math', () => {
  const sampleBox = {
    ymin: 100,
    xmin: 200,
    ymax: 400,
    xmax: 700,
  };

  it('accurately scales normalized 0-1000 coordinates to viewport pixels at 1.0 zoom', () => {
    const scaled = scaleBoundingBox(sampleBox, {
      renderedWidth: 500,
      renderedHeight: 700,
      zoomLevel: 1.0,
    });

    // top = (100 / 1000) * 700 = 70
    expect(scaled.top).toBe(70);
    // left = (200 / 1000) * 500 = 100
    expect(scaled.left).toBe(100);
    // height = ((400 - 100) / 1000) * 700 = 210
    expect(scaled.height).toBe(210);
    // width = ((700 - 200) / 1000) * 500 = 250
    expect(scaled.width).toBe(250);
  });

  it('accurately scales coordinates with zoomLevel = 1.5', () => {
    const scaled = scaleBoundingBox(sampleBox, {
      renderedWidth: 500,
      renderedHeight: 700,
      zoomLevel: 1.5,
    });

    // effectiveWidth = 750, effectiveHeight = 1050
    expect(scaled.top).toBe(105);
    expect(scaled.left).toBe(150);
    expect(scaled.height).toBe(315);
    expect(scaled.width).toBe(375);
  });

  it('sanitizes coordinates exceeding boundaries or inverted bounds', () => {
    const invertedBox = {
      ymin: 800,
      xmin: 600,
      ymax: 300, // ymax < ymin
      xmax: 1500, // xmax > 1000
    };

    const sanitized = sanitizeBoundingBox(invertedBox);
    expect(sanitized.ymin).toBe(800);
    expect(sanitized.ymax).toBe(800); // clamped to ymin
    expect(sanitized.xmax).toBe(1000); // clamped to 1000
    expect(sanitized.xmin).toBe(600);
  });

  it('validates conforming BoundingBoxDTO objects', () => {
    expect(isValidBoundingBox(sampleBox)).toBe(true);
    expect(isValidBoundingBox(null)).toBe(false);
    expect(isValidBoundingBox({ ymin: -5, xmin: 0, ymax: 500, xmax: 500 })).toBe(false);
    expect(isValidBoundingBox({ ymin: 200, xmin: 100, ymax: 100, xmax: 500 })).toBe(false);
  });

  it('calculates bounding box center point accurately', () => {
    const scaled = {
      top: 100,
      left: 100,
      width: 200,
      height: 300,
    };

    const center = calculateBoundingBoxCenter(scaled);
    expect(center.centerX).toBe(200);
    expect(center.centerY).toBe(250);
  });

  it('formats confidence percentages correctly', () => {
    expect(formatConfidence(0.967)).toBe('97%');
    expect(formatConfidence(1.0)).toBe('100%');
    expect(formatConfidence(0.0)).toBe('0%');
    expect(formatConfidence(NaN)).toBe('0%');
  });
});
