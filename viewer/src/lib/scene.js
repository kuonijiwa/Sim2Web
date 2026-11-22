// vtk.js scene: one actor per index layer, one section actor, colouring, camera,
// hardware picking, screenshots and frame-rate measurement.
import '@kitware/vtk.js/Rendering/Profiles/Geometry';
import vtkGenericRenderWindow from '@kitware/vtk.js/Rendering/Misc/GenericRenderWindow';
import vtkActor from '@kitware/vtk.js/Rendering/Core/Actor';
import vtkMapper from '@kitware/vtk.js/Rendering/Core/Mapper';
import vtkColorTransferFunction from '@kitware/vtk.js/Rendering/Core/ColorTransferFunction';
import vtkAxesActor from '@kitware/vtk.js/Rendering/Core/AxesActor';
import vtkOrientationMarkerWidget from '@kitware/vtk.js/Interaction/Widgets/OrientationMarkerWidget';
import vtkSphereSource from '@kitware/vtk.js/Filters/Sources/SphereSource';
import { FieldAssociations } from '@kitware/vtk.js/Common/DataModel/DataSet/Constants';
import { bandedNodes, categoryNodes } from './colormaps.js';

const NEUTRAL = [0.78, 0.78, 0.78];

export class Scene {
  constructor(container, { background = [1, 1, 1] } = {}) {
    this.grw = vtkGenericRenderWindow.newInstance({ background, listenWindowResize: true });
    this.grw.setContainer(container);
    this.renderer = this.grw.getRenderer();
    this.renderWindow = this.grw.getRenderWindow();
    this.glWindow = this.grw.getApiSpecificRenderWindow();
    this.interactor = this.grw.getInteractor();
    this.lut = vtkColorTransferFunction.newInstance();
    this.actors = new Map(); // id -> { actor, mapper, data }
    this.coloring = null;
    this.selector = null;

    const axes = vtkAxesActor.newInstance();
    this.axesWidget = vtkOrientationMarkerWidget.newInstance({ actor: axes, interactor: this.interactor });
    this.axesWidget.setViewportCorner(vtkOrientationMarkerWidget.Corners.TOP_RIGHT);
    this.axesWidget.setViewportSize(0.12);
    this.axesWidget.setEnabled(true);

    this.marker = this.#makeMarker();
    this.grw.resize();
    this.resizeObserver = new ResizeObserver(() => { this.grw.resize(); this.render(); });
    this.resizeObserver.observe(container);
  }

  #makeMarker() {
    const source = vtkSphereSource.newInstance({ thetaResolution: 16, phiResolution: 16, radius: 1 });
    const mapper = vtkMapper.newInstance();
    mapper.setInputConnection(source.getOutputPort());
    const actor = vtkActor.newInstance({ mapper });
    actor.getProperty().setColor(0.05, 0.05, 0.05);
    actor.setVisibility(false);
    actor.setPickable(false);
    this.renderer.addActor(actor);
    return { source, actor };
  }

  ensureActor(id) {
    if (!this.actors.has(id)) {
      const mapper = vtkMapper.newInstance({ lookupTable: this.lut, useLookupTableScalarRange: true });
      const actor = vtkActor.newInstance({ mapper });
      actor.setVisibility(false);
      this.renderer.addActor(actor);
      this.actors.set(id, { actor, mapper, data: null });
    }
    return this.actors.get(id);
  }

  setData(id, polydata) {
    const entry = this.ensureActor(id);
    entry.data = polydata;
    entry.mapper.setInputData(polydata);
    if (this.coloring) this.#colorActor(entry);
  }

  setVisible(id, visible) {
    const entry = this.ensureActor(id);
    entry.actor.setVisibility(Boolean(visible && entry.data));
  }

  setOpacity(id, opacity) {
    this.ensureActor(id).actor.getProperty().setOpacity(opacity);
  }

  setEdges(on) {
    for (const { actor } of this.actors.values()) {
      actor.getProperty().setEdgeVisibility(on);
      actor.getProperty().setEdgeColor(0.25, 0.25, 0.25);
    }
  }

  // coloring = { name, association: 'point'|'cell', kind: 'continuous'|'categorical',
  //              min, max, bands, colormap, categories }
  applyColoring(coloring) {
    this.coloring = coloring;
    this.lut.removeAllPoints();
    const { nodes, legend } = coloring.kind === 'categorical'
      ? categoryNodes(coloring.categories)
      : bandedNodes(coloring.min, coloring.max, coloring.bands, coloring.colormap);
    for (const [x, r, g, b] of nodes) this.lut.addRGBPoint(x, r, g, b);
    for (const entry of this.actors.values()) this.#colorActor(entry);
    return legend;
  }

  #colorActor(entry) {
    const { mapper, actor, data } = entry;
    const c = this.coloring;
    if (!data || !c) return;
    const container = c.association === 'cell' ? data.getCellData() : data.getPointData();
    const array = container.getArrayByName(c.name);
    if (!array) {
      // the product does not carry this field: show it uncoloured
      mapper.setScalarVisibility(false);
      actor.getProperty().setColor(...NEUTRAL);
      return;
    }
    mapper.setScalarVisibility(true);
    mapper.setColorByArrayName(c.name);
    mapper.setColorModeToMapScalars();
    if (c.association === 'cell') mapper.setScalarModeToUseCellFieldData();
    else mapper.setScalarModeToUsePointFieldData();
    // point fields: interpolate before mapping so band edges stay sharp
    mapper.setInterpolateScalarsBeforeMapping(c.association === 'point');
  }

  render() {
    this.renderWindow.render();
  }

  // ------------------------------------------------------------------ camera
  visibleBounds() {
    return this.renderer.computeVisiblePropBounds();
  }

  resetCamera() {
    const camera = this.renderer.getActiveCamera();
    const b = this.visibleBounds();
    if (!(b[0] <= b[1])) return;
    const c = [(b[0] + b[1]) / 2, (b[2] + b[3]) / 2, (b[4] + b[5]) / 2];
    const d = Math.max(b[1] - b[0], b[3] - b[2], b[5] - b[4], 1e-6) * 2.5;
    camera.setFocalPoint(...c);
    camera.setPosition(c[0] - 0.6 * d, c[1] - 0.6 * d, c[2] + 1.2 * d);
    camera.setViewUp(0, 0, 1);
    this.renderer.resetCamera();
    camera.zoom(0.9);
    this.renderer.resetCameraClippingRange();
    this.render();
  }

  viewAxis(axis, bounds = this.visibleBounds()) {
    if (!(bounds[0] <= bounds[1])) return;
    const camera = this.renderer.getActiveCamera();
    const c = [(bounds[0] + bounds[1]) / 2, (bounds[2] + bounds[3]) / 2, (bounds[4] + bounds[5]) / 2];
    const span = Math.max(bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4]) || 1;
    const d = span * 2;
    camera.setFocalPoint(...c);
    if (axis === 'x') { camera.setPosition(c[0] + d, c[1], c[2]); camera.setViewUp(0, 0, 1); }
    if (axis === 'y') { camera.setPosition(c[0], c[1] + d, c[2]); camera.setViewUp(0, 0, 1); }
    if (axis === 'z') { camera.setPosition(c[0], c[1], c[2] + d); camera.setViewUp(0, 1, 0); }
    this.renderer.resetCamera(bounds);
    camera.zoom(0.9);
    this.renderer.resetCameraClippingRange();
    this.render();
  }

  setParallel(on) {
    this.renderer.getActiveCamera().setParallelProjection(on);
    this.renderer.resetCameraClippingRange();
    this.render();
  }

  getCamera() {
    const cam = this.renderer.getActiveCamera();
    return [...cam.getPosition(), ...cam.getFocalPoint(), ...cam.getViewUp(), cam.getParallelScale()];
  }

  setCamera(v) {
    const cam = this.renderer.getActiveCamera();
    cam.setPosition(v[0], v[1], v[2]);
    cam.setFocalPoint(v[3], v[4], v[5]);
    cam.setViewUp(v[6], v[7], v[8]);
    cam.setParallelScale(v[9]);
    this.renderer.resetCameraClippingRange();
    this.render();
  }

  // ----------------------------------------------------------------- picking
  async pick(displayX, displayY) {
    if (!this.selector) {
      this.selector = this.glWindow.createSelector();
      this.selector.setFieldAssociation(FieldAssociations.FIELD_ASSOCIATION_CELLS);
      this.selector.setCaptureZValues(true);
    }
    const [x, y] = [Math.round(displayX), Math.round(displayY)];
    const result = await this.selector.getSourceDataAsync(this.renderer, x, y, x, y);
    if (!result) return null;
    const selections = result.generateSelection(x, y, x, y);
    if (!selections?.length) return null;
    const props = selections[0].getProperties();
    const hit = [...this.actors.entries()].find(([, e]) => e.actor === props.prop);
    if (!hit) return null;
    return { id: hit[0], data: hit[1].data, cellId: props.attributeID, position: props.worldPosition || null };
  }

  showMarker(position, radius) {
    if (!position) { this.marker.actor.setVisibility(false); this.render(); return; }
    this.marker.source.setCenter(...position);
    this.marker.source.setRadius(radius);
    this.marker.actor.setVisibility(true);
    this.render();
  }

  // Browser-level verification: what each visible actor is actually coloured by.
  describeActors() {
    const out = {};
    for (const [id, { actor, mapper, data }] of this.actors.entries()) {
      if (!actor.getVisibility() || !data) continue;
      const mode = mapper.getScalarMode();
      const byCell = mode === 2 || mode === 4; // USE_CELL_DATA / USE_CELL_FIELD_DATA
      const name = mapper.getColorByArrayName();
      const container = byCell ? data.getCellData() : data.getPointData();
      const array = mapper.getScalarVisibility() ? container.getArrayByName(name) : null;
      out[id] = {
        scalarVisibility: mapper.getScalarVisibility(), array: name, association: byCell ? 'cell' : 'point',
        arrayFound: Boolean(array), dataRange: array ? array.getRange() : null,
        lutRange: this.lut.getMappingRange(), points: data.getNumberOfPoints(), cells: data.getNumberOfCells(),
      };
    }
    return out;
  }

  // ------------------------------------------------------------- utilities
  async screenshot() {
    const [image] = await this.renderWindow.captureImages();
    return image;
  }

  // Rotate the camera through `frames` steps of `degrees` and report frames per second.
  async measureFrameRate(frames = 120, degrees = 3) {
    const camera = this.renderer.getActiveCamera();
    const t0 = performance.now();
    for (let i = 0; i < frames; i += 1) {
      camera.azimuth(degrees);
      this.renderer.resetCameraClippingRange();
      this.render();
      // eslint-disable-next-line no-await-in-loop
      await new Promise((r) => requestAnimationFrame(r));
    }
    const seconds = (performance.now() - t0) / 1000;
    return { frames, seconds, fps: frames / seconds };
  }

  canvasSize() {
    return this.glWindow.getSize();
  }
}
