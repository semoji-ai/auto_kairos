"""앵커 댓글이 달린 .docx 생성 — 구글 문서 변환 시 댓글이 보존된다.

Drive API의 comments.create는 구글 문서(kix)의 내부 앵커 체계를 만들지 못해서,
만들어도 문서 UI에 표시되지 않는다(무앵커 댓글). Apps Script도 같은 API를 쓰므로 동일.

우회 경로: .docx는 댓글을 포맷 자체에 담는다(word/comments.xml + commentRangeStart/End).
구글 드라이브가 docx → 구글 문서로 변환할 때 이 댓글과 앵커를 그대로 가져온다.

사용:
    from auto_agent.tools.docx_comments import build_docx
    build_docx(paragraphs, comments, out_path)
        paragraphs: list[str]  — 문단(빈 문자열이면 빈 줄)
        comments:   list[tuple[int, str]] — (문단 인덱스, 댓글 본문)
"""
from __future__ import annotations

import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/comments.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"/>
</Types>"""

ROOT_RELS = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="{R_NS}/officeDocument" Target="word/document.xml"/>
</Relationships>"""

DOC_RELS = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="{R_NS}/comments" Target="comments.xml"/>
</Relationships>"""


def _para(text: str, cid: int | None = None, heading: bool = False) -> str:
    """문단 XML. cid가 있으면 이 문단 전체를 댓글 범위로 감싼다.

    heading=True면 굵게·크게 + 위아래 여백을 준다. 챕터 제목이 본문과
    구분되지 않으면 낭독 대본에서 장 경계를 찾을 수 없다.
    """
    t = escape(text)
    if text:
        rpr = '<w:rPr><w:b/><w:sz w:val="30"/></w:rPr>' if heading else ''
        run = f'<w:r>{rpr}<w:t xml:space="preserve">{t}</w:t></w:r>'
    else:
        run = ''
    ppr = '<w:pPr><w:spacing w:before="360" w:after="120"/></w:pPr>' if heading else ''
    if cid is None:
        return f'<w:p>{ppr}{run}</w:p>'
    return (
        f'<w:p>{ppr}'
        f'<w:commentRangeStart w:id="{cid}"/>'
        f'{run}'
        f'<w:commentRangeEnd w:id="{cid}"/>'
        f'<w:r><w:commentReference w:id="{cid}"/></w:r>'
        f'</w:p>'
    )


def build_docx(paragraphs: list[str], comments: list[tuple[int, str]], out: Path,
               headings: set[int] | None = None) -> Path:
    """댓글이 달린 docx 생성.

    comments: (문단 인덱스, 댓글 본문) 목록. 같은 문단에 여러 개도 가능하지만
              docx 규격상 범위가 겹치므로 문단당 하나로 합쳐 넘기는 편이 안전하다.
    """
    by_para: dict[int, int] = {}
    comment_parts = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for cid, (pidx, body) in enumerate(comments):
        by_para[pidx] = cid
        lines = ''.join(
            f'<w:p><w:r><w:t xml:space="preserve">{escape(l)}</w:t></w:r></w:p>'
            for l in body.split('\n')
        )
        comment_parts.append(
            f'<w:comment w:id="{cid}" w:author="auto-kairos" '
            f'w:date="{now}" w:initials="AK">{lines}</w:comment>'
        )

    hs = headings or set()
    body_xml = ''.join(
        _para(p, by_para.get(i), heading=(i in hs)) for i, p in enumerate(paragraphs)
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{W_NS}"><w:body>{body_xml}'
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/></w:sectPr>'
        '</w:body></w:document>'
    )
    comments_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:comments xmlns:w="{W_NS}">{"".join(comment_parts)}</w:comments>'
    )

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', CONTENT_TYPES)
        z.writestr('_rels/.rels', ROOT_RELS)
        z.writestr('word/document.xml', document)
        z.writestr('word/_rels/document.xml.rels', DOC_RELS)
        z.writestr('word/comments.xml', comments_xml)
    return out
