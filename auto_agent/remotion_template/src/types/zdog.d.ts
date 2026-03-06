declare module "zdog" {
  interface Vector {
    x?: number;
    y?: number;
    z?: number;
  }

  interface AnchorOptions {
    addTo?: Anchor;
    translate?: Vector;
    rotate?: Vector;
    scale?: number | Vector;
    color?: string;
    visible?: boolean;
  }

  interface ShapeOptions extends AnchorOptions {
    stroke?: number | false;
    fill?: boolean;
    closed?: boolean;
    path?: any[];
    front?: Vector;
    backface?: string | boolean;
  }

  interface EllipseOptions extends ShapeOptions {
    diameter?: number;
    width?: number;
    height?: number;
    quarters?: number;
  }

  interface RectOptions extends ShapeOptions {
    width?: number;
    height?: number;
  }

  interface RoundedRectOptions extends RectOptions {
    cornerRadius?: number;
  }

  interface HemisphereOptions extends ShapeOptions {
    diameter?: number;
  }

  interface ConeOptions extends ShapeOptions {
    diameter?: number;
    length?: number;
  }

  interface CylinderOptions extends ShapeOptions {
    diameter?: number;
    length?: number;
    frontFace?: string | boolean;
    backface?: string | boolean;
  }

  interface BoxOptions extends ShapeOptions {
    width?: number;
    height?: number;
    depth?: number;
    frontFace?: string;
    rearFace?: string;
    leftFace?: string;
    rightFace?: string;
    topFace?: string;
    bottomFace?: string;
  }

  interface IllustrationOptions extends AnchorOptions {
    element?: HTMLCanvasElement | SVGSVGElement;
    zoom?: number;
    centered?: boolean;
    dragRotate?: boolean | Anchor;
    resize?: boolean;
    onPrerender?: (ctx: CanvasRenderingContext2D) => void;
    onDragStart?: () => void;
    onDragMove?: () => void;
    onDragEnd?: () => void;
  }

  class Anchor {
    constructor(options?: AnchorOptions);
    addChild(child: Anchor): void;
    removeChild(child: Anchor): void;
    remove(): void;
    copy(options?: AnchorOptions): Anchor;
    copyGraph(options?: AnchorOptions): Anchor;
    translate: Vector;
    rotate: Vector;
    scale: number | Vector;
    children: Anchor[];
    updateGraph(): void;
    renderGraphCanvas(ctx: CanvasRenderingContext2D): void;
    normalizeRotate(): void;
  }

  class Shape extends Anchor {
    constructor(options?: ShapeOptions);
    stroke: number | false;
    fill: boolean;
    color: string;
    path: any[];
  }

  class Ellipse extends Shape {
    constructor(options?: EllipseOptions);
    diameter: number;
    quarters: number;
  }

  class Rect extends Shape {
    constructor(options?: RectOptions);
    width: number;
    height: number;
  }

  class RoundedRect extends Shape {
    constructor(options?: RoundedRectOptions);
    width: number;
    height: number;
    cornerRadius: number;
  }

  class Hemisphere extends Shape {
    constructor(options?: HemisphereOptions);
    diameter: number;
  }

  class Cone extends Shape {
    constructor(options?: ConeOptions);
    diameter: number;
    length: number;
  }

  class Cylinder extends Shape {
    constructor(options?: CylinderOptions);
    diameter: number;
    length: number;
  }

  class Box extends Shape {
    constructor(options?: BoxOptions);
    width: number;
    height: number;
    depth: number;
  }

  class Group extends Anchor {
    constructor(options?: AnchorOptions);
    visible: boolean;
    updateSort: boolean;
  }

  class Illustration extends Anchor {
    constructor(options?: IllustrationOptions);
    element: HTMLCanvasElement | SVGSVGElement;
    zoom: number;
    centered: boolean;
    updateRenderGraph(): void;
    setSize(width: number, height: number): void;
    renderGraphCanvas(ctx: CanvasRenderingContext2D): void;
  }

  const TAU: number;

  export {
    Anchor,
    Shape,
    Ellipse,
    Rect,
    RoundedRect,
    Hemisphere,
    Cone,
    Cylinder,
    Box,
    Group,
    Illustration,
    TAU,
  };

  export default {
    Anchor,
    Shape,
    Ellipse,
    Rect,
    RoundedRect,
    Hemisphere,
    Cone,
    Cylinder,
    Box,
    Group,
    Illustration,
    TAU,
  };
}
