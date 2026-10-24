// macOS Vision OCR: usage: [OCR_LANGS=zh-Hans,en-US] ocr <png>... → JSON lines {"file","w","h","items":[{"text","conf","box":[x,y,w,h] (픽셀, 왼쪽 위 기준)}]}
import Foundation
import Vision
import AppKit
for path in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: path), let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        print("{\"file\":\"\(path)\",\"error\":\"load\"}"); continue }
    let W = Double(cg.width), H = Double(cg.height)
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    // 인식 언어(기본 한국어·영어). 중국어판 검사 등은 OCR_LANGS 환경변수로(예: zh-Hans,en-US)
    let langs = ProcessInfo.processInfo.environment["OCR_LANGS"].map { $0.split(separator: ",").map(String.init) } ?? ["ko-KR", "en-US"]
    req.recognitionLanguages = langs
    req.usesLanguageCorrection = false
    try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
    var items: [[String: Any]] = []
    for o in (req.results ?? []) {
        guard let c = o.topCandidates(1).first else { continue }
        let b = o.boundingBox
        let pt = { (p: CGPoint) -> [Double] in [Double(p.x) * W, (1 - Double(p.y)) * H] }
        items.append(["text": c.string, "conf": c.confidence,
                      "box": [b.minX * W, (1 - b.maxY) * H, b.width * W, b.height * H],
                      "quad": [pt(o.topLeft), pt(o.topRight), pt(o.bottomRight), pt(o.bottomLeft)]])
    }
    let d: [String: Any] = ["file": path, "w": W, "h": H, "items": items]
    let data = try! JSONSerialization.data(withJSONObject: d)
    print(String(data: data, encoding: .utf8)!)
}
