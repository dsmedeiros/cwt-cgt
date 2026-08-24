"""Static lane firewall for the sealed response-adapter source tree."""

from __future__ import annotations

import ast
import hashlib
import stat
import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
SIM_ROOT = PACKAGE_DIR.parents[1]
CURRENT_PACKAGE = "experiments.generator_tensor_response_protocol"
PREDICTOR_PACKAGE = "experiments.generator_tensor_prediction_protocol"
PRODUCER_PACKAGE = "experiments.loop_flux_counting_curvature_proof"

EXPECTED_PACKAGE_FILES = (
    "MODEL_CONTRACT.md",
    "__init__.py",
    "anchors.py",
    "authority.py",
    "broker.py",
    "contract.py",
    "exact.py",
    "firewall.py",
    "fit.py",
    "geometry_plan.py",
    "protocol.py",
    "run.py",
    "theorem.py",
)
FOCUSED_TEST_RELATIVE = "tests/experiments/test_generator_tensor_response_protocol.py"

# These digests freeze closed, version-neutral AST capability inventories for
# every reviewed Python material. Constant payloads are typed but deliberately
# omitted from the AST domain; exact bytes are publication-bound later by the
# external Git SOURCE_LOCK. This in-package table is defense-in-depth and is
# not an independent source authority.
_REVIEWED_SOURCE_STRUCTURE_SHA256 = {
    "__init__.py": "a77b2fb967c86ed9850e3709ee25f4e25f5ba3dbc827b0841e80a8b27c125d27",
    "anchors.py": "65a613bfc1a80810a116eeae26e3b4728a29a04c83b009fe0f55a0fbfca09219",
    "authority.py": "e3bde0b700e7d63ecbf306a02d76eaa6556a2c079cdf87647ca4a4e2efce649d",
    "broker.py": "5cda582901f227462b6d820c57b40e04882bd228f93a32e6dd15e9cf35560378",
    "contract.py": "6a0eb6f44256ae6c3415659d049d3796816d7b84277c9576e9ec84da31456b9f",
    "exact.py": "66ec81ae5ac440687e10b6d27afe337890b8954d860f01dc38d13fd9eba08d43",
    "firewall.py": "19ac5e79e57bb59ce4404f41e5f1fe2ecb3461b970c186436fadb1da9d1b11c9",
    "fit.py": "0d2adf4a194d113e59a089fe722e77a309052ca65947c286e881fb664d7f27b0",
    "geometry_plan.py": "f2edc6db6d8393483551d4b4966eab3cb24e3d57d65682edbf0d71b2fda85595",
    "protocol.py": "e310ad60dd81cd5c67c8a946b1fabc45c559159024bb4d7e1240f6f663e023d5",
    "run.py": "6b36b70bcb66028a440e8f3907480f6bbedaea66ec51d5b562eaccf3645db7f2",
    "theorem.py": "39006c284a991b6376a558524444caee8bd399ac5e7130376856ad0362cc7f85",
    FOCUSED_TEST_RELATIVE: "ab9865f2ba95d9b2cb71baec73d6e7410e036de63053c14dd1d8adb4df9515c4",
}
_REVIEWED_MODEL_CONTRACT_SHA256 = "c151dd7e1e6a79a3f907732aac5e53b6f897e56734bc8a7d30523ce15c832d3a"
_REVIEWED_STRUCTURE_AGGREGATE_SHA256 = "e647ba1b4881b20f9b693bcb1bf7f5aa7bcd83cb7338585d6b58bea7ba5339fe"

ROLE_FILES = {
    "support": ("__init__.py", "contract.py", "exact.py"),
    "anchor": ("anchors.py",),
    "authority": ("authority.py",),
    "broker": ("broker.py",),
    "geometry": ("geometry_plan.py",),
    "fit": ("fit.py",),
    "protocol": ("protocol.py",),
    "composition": ("theorem.py", "run.py"),
    "firewall_authority": ("firewall.py",),
    "focused_test": (FOCUSED_TEST_RELATIVE,),
}
MATERIAL_FILES = (
    ("contract_document", "MODEL_CONTRACT.md", "markdown"),
    ("support", "__init__.py", "python"),
    ("anchor", "anchors.py", "python"),
    ("authority", "authority.py", "python"),
    ("broker", "broker.py", "python"),
    ("support", "contract.py", "python"),
    ("support", "exact.py", "python"),
    ("firewall_authority", "firewall.py", "python"),
    ("fit", "fit.py", "python"),
    ("geometry", "geometry_plan.py", "python"),
    ("protocol", "protocol.py", "python"),
    ("composition", "run.py", "python"),
    ("composition", "theorem.py", "python"),
    ("focused_test", FOCUSED_TEST_RELATIVE, "python"),
)

_DYNAMIC_CAPABILITIES = {
    "__import__",
    "breakpoint",
    "compile",
    "eval",
    "exec",
    "getattr",
    "globals",
    "input",
    "locals",
    "open",
    "setattr",
    "vars",
}
_PROCESS_OR_NETWORK_ROOTS = {
    "asyncio",
    "ctypes",
    "http",
    "io",
    "importlib",
    "marshal",
    "multiprocessing",
    "os",
    "pickle",
    "runpy",
    "socket",
    "subprocess",
    "sys",
    "urllib",
}
_CONTROLLED_MODULE_ROOTS = _PROCESS_OR_NETWORK_ROOTS | {
    "builtins",
    "dis",
    "inspect",
    "threading",
}
_PATH_CONSTRUCTORS = {"Path", "PurePosixPath"}
_PATH_CAPABILITY_ATTRIBUTES = {
    "absolute",
    "chmod",
    "cwd",
    "exists",
    "glob",
    "hardlink_to",
    "home",
    "is_dir",
    "is_file",
    "is_symlink",
    "iterdir",
    "joinpath",
    "lchmod",
    "link_to",
    "lstat",
    "mkdir",
    "open",
    "owner",
    "parser",
    "read",
    "read1",
    "read_bytes",
    "read_text",
    "readinto",
    "readline",
    "readlines",
    "readlink",
    "relative_to",
    "rename",
    "replace",
    "resolve",
    "rglob",
    "rmdir",
    "samefile",
    "scandir",
    "stat",
    "symlink_to",
    "touch",
    "unlink",
    "walk",
    "write_bytes",
    "write_text",
}
_REVIEWED_PATHLIB_IMPORTS = {
    ("anchor", "anchors.py"): (("Path", None), ("PurePosixPath", None)),
    ("authority", "authority.py"): (("Path", None), ("PurePosixPath", None)),
    ("firewall_authority", "firewall.py"): (("Path", None),),
    ("composition", "run.py"): (("Path", None),),
    ("composition", "theorem.py"): (("Path", None),),
    ("focused_test", FOCUSED_TEST_RELATIVE): (("Path", None),),
}
_REVIEWED_CAPABILITY_IMPORTS = {
    ("anchor", "anchors.py"): frozenset(
        {
            ("import", (("builtins", None),)),
            ("import", (("dis", None),)),
            ("import", (("inspect", None),)),
            ("import", (("sys", None),)),
            ("import", (("threading", None),)),
            (
                "from:0:importlib.machinery",
                (("ModuleSpec", None), ("SourceFileLoader", None)),
            ),
        }
    ),
    ("authority", "authority.py"): frozenset(
        {
            ("import", (("os", None),)),
            ("import", (("shutil", None),)),
            ("import", (("subprocess", None),)),
            ("import", (("sys", None),)),
        }
    ),
    ("broker", "broker.py"): frozenset({("import", (("sys", None),))}),
    ("firewall_authority", "firewall.py"): frozenset({("import", (("sys", None),))}),
    ("composition", "run.py"): frozenset({("import", (("sys", None),))}),
    ("composition", "theorem.py"): frozenset({("import", (("sys", None),))}),
    ("focused_test", FOCUSED_TEST_RELATIVE): frozenset(
        {
            ("import", (("importlib.util", None),)),
            ("import", (("inspect", None),)),
            ("import", (("sys", None),)),
        }
    ),
}
_REVIEWED_PATH_STATEMENT_SHA256: dict[tuple[str, str], frozenset[str]] = {
    ("anchor", "anchors.py"): frozenset(
        {
            "03ebe4988279e8c8bff744572172094364efdd1c4e74770fd9e54fbc9a750306",
            "098b127376a6c27d5dbb628fa4411aa1296bda2fac5725419cb6d96f26638371",
            "1c945613200791419bb6bacaa5c78dd5143eb0c8dbfa8965989396187d32c058",
            "20f7a6336f931fce3780b7629e4faef256a3c3f49bdc18f775643ac469d08d53",
            "264c9ede4756db96250c23308bfeb7d1062f5cd0bbb6c4000f8b5b7c5344a9fd",
            "39b82fc822838807c509f429f407b1c588890f3362e2f0b357d503e1f3d5d233",
            "3ace14969da353cf8d77ab6f5dbecc1020492075722d3bdf34d9ab9c749151ea",
            "402a767be90b4760d9e57fac31561f1a48843e702cbba1134ff689c42f8ed599",
            "7010e8b761d964292db65c9b3ff7ac80d8bdc5101f2643d7b0b7c6d8e55766b7",
            "729c1ecfe268901a59bec7e3ea2148828baf209eb4d4dac458426f10a26f67b8",
            "7cafa7d15d74451cc78b2ae94c7de2547b2981530b6cffb58c3f98742752abfa",
            "abfc5594fabd778eb5b327ecfc1ae4be3c1703869cd52c877d0a976a2da99471",
            "b1d3490d3b5eb6c866c8ff62fb5f56dc0174428923300f171bcd020dba916c16",
            "ba95eb47a70224e6ec057790b6c078f9c429bdcbd65eaa0f7b8a826c9b8ce132",
            "d1c59ca3d033a77fb5132dac96bf194c714a7ea12b6bb6bd20d832df69603c9a",
            "df072f355dfe9c0cea868f1bea42c9b337f3e629e22db15bdd83b1698e998fe8",
        }
    ),
    ("authority", "authority.py"): frozenset(
        {
            "04d55a6d10748920b06f327d638072c35424abe1b19d5e46b2589c8514acc6bf",
            "1690a7496d7cd2c3b9618afd6ceef3adb05c1c0685f2929ce8e32a1a94f82aa3",
            "18b6bba546b3f671956fa824a6c699eedfe47bd4e9a0ab3aa7bfe984b436654a",
            "24123e25d385a9807a8039cf2b9ea6c1d9f5ffb2a17cba38f815e493ef787cf1",
            "28b9873010dd6a2cd069ccc58426988081f77e3c8c5c4dd88da326eed5190a09",
            "2e4465aeec837d0be7b852834c10cc0b3ab2a9068cbaedce6d1f29259ca60023",
            "3ace14969da353cf8d77ab6f5dbecc1020492075722d3bdf34d9ab9c749151ea",
            "3f5c30d453c5e704e0986fe6c03e23c71704ef91260f4d04d69f171ae74198e8",
            "42e213d8dec6e6695da34b936d2f3e6be168be14daffa244d27e875daae92824",
            "4852c9222946cbd2840f2e37875efc75f53bd2ccdc3862c46d41ba0d4b50d5ae",
            "4afbd08693a341a019f498934d9044bc245040b35dfb4701266ce21a6f18d192",
            "4b61e0cc88bd901cee5ddf68beecbf386679aa3d0b1eda55d8ae5cce748b8440",
            "4bfd96528aa30aa7fb61440b086563ba78ca7af54c08f4d675be3022c4b3437f",
            "4d0334c955ace1c31903cfe1af30f74ad4bce7b7ace075a9be7bd3b2f05933cf",
            "573e4aa3de7e919965598ce35564f55fb0fd2ee11eb0e838ef8d82e1278255f0",
            "599c7b9fc39e96a5f7f24ca8749cb29d07ce26ad73c0c2f9b9bba9ef39ba6ae6",
            "6ddbc67aaf24837ae7c64787b105487a7a61e0e4780df944c03d8f5715b23300",
            "7ab4051dfcdb6d7935df7c0e7c633597b5c994a5f9c01bdd82f2252b71e7a70d",
            "8907f0c5c7f7f783cc50ac7e6f3f6e08412acc026327257c935a963947369e39",
            "9f0326af6dfaf058c1b2cc36a8dcad95b9c4bc0421d98e376303e8c6741dad94",
            "9f4c636d4a20ee2d1b77cb99ba34640b31be1fa23caf875fcc41b0894eb8fa19",
            "a53b48fa0a6dceaa422b17f4fa540ba042294233dbddf1b45f6dd1f1de529bd1",
            "b3de06797f58efade7b6c76cc4beeeae4cf54b117f08435a3a5255d1d637e8df",
            "b9b57e95ef7e6d98ba4a541ca78ad5e7a0ef3627114c2c0804669d6ed4503dde",
            "bb1b25cf3d4f6eca0401b869cf857930ab7c6e1f003c0478f474a6caba40001c",
            "cae3742e4d4f79201c3ba7f6b4e57ee3ae3fbe43030b5ec9dd09c2f876401c40",
            "cb97d6c0dc1a5e500fe944cd05b8330f32a0548832ff05f427e1150e85c81420",
            "cdce3f5bbe9b177f57c00b1f3136b5fcaaafe034882ad7c2eebfd6e85cdf81be",
            "d59889dd73bab852dc1cd2033fb14437881f099458d80f6ebb8421c0075ef560",
            "f14dddc76f1353df1d2bcdb18ebf605daf421c1e72fcf8b4bde914adef8d1920",
            "f932b905e670b98bc58203cadc64cbdd0a37fd9018e9db7ef02c84f911bffe3c",
            "fc602ef69e14262320d34b1ea94ce238b28de723e257c0611c7ed42fc831ecf7",
        }
    ),
    ("broker", "broker.py"): frozenset({"d3dd9f978bbec9d7a7252f23c343ab4ab9bdcbc34df719459e0a52ed72baf290"}),
    ("firewall_authority", "firewall.py"): frozenset(
        {
            "0bfdc0c39f535a0a21f009502115be24a7f8ebb52e9603832c48ae1dc4b5b78c",
            "20ddeac94248f3f67b4db0c338788582f55067ad30f6bd2e5ecb3c2b13087247",
            "39b82fc822838807c509f429f407b1c588890f3362e2f0b357d503e1f3d5d233",
            "3ace14969da353cf8d77ab6f5dbecc1020492075722d3bdf34d9ab9c749151ea",
            "5a2aa906042b63f2bc43fa5c820bd127a961f29afc31a5fa331d757017a3beb1",
            "a53b48fa0a6dceaa422b17f4fa540ba042294233dbddf1b45f6dd1f1de529bd1",
            "daf69789f3a1fc1f2cfd358439b49e728bff1225e29a87d7d36853f6116646b4",
            "df6d245d94bb6485dcff0268ceae17e44eab591a235a399e1608ed95fcb028c0",
            "fe39bfde48fd3c30748d039a95bb05dcb916eccfbedfd77d788695e3306ede90",
            "ffb78e1894da7a9ffb6ca99451d606d9626ab5724b083bc71d805eaab665eb2c",
        }
    ),
    ("composition", "run.py"): frozenset(
        {"2baf17bf04ae7735a309e4bea967490112ef4bc5d38f2861fdfbbf8983abb2a2"}
    ),
    ("composition", "theorem.py"): frozenset(
        {
            "3ace14969da353cf8d77ab6f5dbecc1020492075722d3bdf34d9ab9c749151ea",
            "43516c6876c9d1e5fd0ced06f4eba8d23f100b8bafcd557bbeb0b02f55b69db9",
            "adb8cbcc3a131667f2cdaa1b10eeceb5aecce62160f48109a55d57e349bc6521",
            "c2dfef69f111b342ddf7368a20562fb1ea2421a3fa7867508c32610c6c80a904",
        }
    ),
    ("focused_test", FOCUSED_TEST_RELATIVE): frozenset(
        {
            "177f1f4464d7066db6caf1f0b419b969411ca10754d9f89f63c52331d38121d3",
            "51fe802fe067aa0719d66093d0ee970512c3847f7f4232dc58a36123f30be140",
            "76e834fc04bf60f88838c003905a346202b95a0d6cfc218b07e5fc2f3313a4a4",
            "795b878d8ffa19e8a077351e6166aa60b2d743b9f70563c82465c92fac3555b1",
            "a53b48fa0a6dceaa422b17f4fa540ba042294233dbddf1b45f6dd1f1de529bd1",
            "bcb44ef6fb01fac8735f714b591196bae5bc11836027fe6bed3a5b0b56095194",
            "cd4630f64c483930b59f657ffae8a8ef3309f73fcc5c14923e57ee81fe4032bc",
            "ce1ac34df35befe7d401570df4787b851f9c63aec8f0f0fdbb6346559577d00c",
            "dacdfefe248217b849a2a6f9cc069df6bfa514e1b6981d68dccf5cbde62ff8d0",
        }
    ),
}
_REVIEWED_CAPABILITY_STATEMENT_SHA256: dict[tuple[str, str], frozenset[str]] = {
    ("anchor", "anchors.py"): frozenset(
        {
            "1dca9d9389e95c5417f05002250efa45fb1ded1b8e08749d58e7e83267929918",
            "250ef4e1525297242f62438724e2ad7108c7032d1dcd88e087e77e5ec8715d0e",
            "41c3d43a6a3bb6658cdbf2a0a67afceb04b09ef721915d6befb7b1b0de91a231",
            "47a91d40251e8b2448d896a39cbbd53fba25d0cc025f487cabddd82de1d87efc",
            "691028fc503ad91683d8a9a196be1af93d93ea2d545f62eb58f86488e90b79b1",
            "7010e8b761d964292db65c9b3ff7ac80d8bdc5101f2643d7b0b7c6d8e55766b7",
            "7969cc0e0dce1218057a3ff043ac6c6aab539d488f8d8c24318ac7ae26b74ff8",
            "864cc47b54b3ab0366fedab857a234d23116eb2cb792bf2c6eb81c075932301f",
            "a16b1421b2b8153321fdf57f76ba845e09af630a97a23909850bb197d31d92ca",
        }
    ),
    ("authority", "authority.py"): frozenset(
        {
            "0f8fa2104c4c134adeae3e380b3ebeac1f2f8b55119140a070708eae84d68e3f",
            "267bd7fbe0e17e38969d57e161cbd0a9892aff48f8a32c23464b85d4b3b9597d",
            "2e847688e27073a0dab11f9d0c9eb26956c1a136a01b16328a02987ef44c7163",
            "4afbd08693a341a019f498934d9044bc245040b35dfb4701266ce21a6f18d192",
            "596cc7259da33ada6312d86964f3b6d6203888087d347a9d1ffdc259e00a56fd",
            "5b3b4f7590708bf3d4d12b79406a2957db5c0a4408259205b3a5169b6ba8e76b",
            "644b4d1d4e2cc6eabe84933d37eb7d593ee95631a287e73ccc6b17d6af87cdd7",
            "65fa05aa0b62de4e9623716757590a551a9dc032ea7033bd401663a5c9126191",
            "6af0167a711b87ef1161b7667ca7e7b843f1a3f0e747165ae71458cfc2b7a55e",
            "828b7762ede9322822178847c2c5b1dcb39723f76bc33563e3861192280b4ea0",
            "876b0830d7b7488eb9b163ebda21f01137b81fad886676e76baa2383ae2ca1ea",
            "8907f0c5c7f7f783cc50ac7e6f3f6e08412acc026327257c935a963947369e39",
            "98999ddece203f6612eb423650f84b7ecec8cc91908e1b9f66a6968be1e85412",
            "9f4c636d4a20ee2d1b77cb99ba34640b31be1fa23caf875fcc41b0894eb8fa19",
            "a15c7186d1e2deddbc05a46369918c2aca8175d3e88ee709892b48b81cb3ad85",
            "ad0b6df44aab9ff664a1f572a59a4d6d30f23c151adc6dacdee7e83c43e6c1e8",
            "b89897bd74de55af3fb5b7af3ed19c6759ac66bbd6e430a23b36ab5ed74ba884",
            "de71008d6d6e05f987763fb2a7fcbcf0b31230e322ca3f7b05eedd72b4c51d6b",
            "e5433e29ce09b828cbc5dd80f674479adeccd4afd5c92934bf78329f2ef4d322",
            "ef463acd06cc6069ebb36f2669c42d78bb16cd13b141e75dd467f9f30c051e22",
        }
    ),
    ("broker", "broker.py"): frozenset(
        {
            "4e1c708bf6de8daa1bcdb8f86c90806b78da9ec57762249825b5b185be682a9f",
            "d3dd9f978bbec9d7a7252f23c343ab4ab9bdcbc34df719459e0a52ed72baf290",
        }
    ),
    ("firewall_authority", "firewall.py"): frozenset(
        {"864cc47b54b3ab0366fedab857a234d23116eb2cb792bf2c6eb81c075932301f"}
    ),
    ("composition", "run.py"): frozenset(
        {"2baf17bf04ae7735a309e4bea967490112ef4bc5d38f2861fdfbbf8983abb2a2"}
    ),
    ("composition", "theorem.py"): frozenset(
        {"acee61a4cecc701ec5fd165947f57069aa62a4fb064d784a95c97d745192de2f"}
    ),
    ("focused_test", FOCUSED_TEST_RELATIVE): frozenset(
        {
            "027577acda7971a144a1e36436506e63fa6f5d19cbda9b7f93d24ddcc56d2c05",
            "53eadb126555a94b962c0b91b7dfe35880d945eb3d74fa020feb81fa96da49bc",
            "768c3473091eedd3aa94fea5e515ea2c26c258a7e8b7e778fd35deb0513f3227",
            "8d5f4bb022b21bdd900a04ad7cf8cc3b8db0ecdd54b1742ad60f49818bacbc57",
            "acee61a4cecc701ec5fd165947f57069aa62a4fb064d784a95c97d745192de2f",
            "b63ad4dac03a9de63d103ae9b4ec388714efa0af19c2e056a21828320fc70f43",
            "b93955c48394d71b82d5d8b66524ca1eca811b20851503e21bb773999f8bbfac",
            "bc011c6498742d3aa6721ccfd2b3511d78d4d02044be93c7bac3ee50360fef8e",
            "ed9a7a57e3547e4fefce5f4851df4433216dd0ade8df830fd0a2f8ecc9e3bcb3",
        }
    ),
}


def _has_reparse(path: Path) -> bool:
    if sys.platform != "win32":
        return path.is_symlink()
    return path.is_symlink() or bool(path.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _import_name(node: ast.Import | ast.ImportFrom) -> tuple[str, ...]:
    if isinstance(node, ast.Import):
        return tuple(alias.name for alias in node.names)
    if node.module is None:
        return ()
    return tuple(f"{node.module}.{alias.name}" for alias in node.names)


def _import_signature(node: ast.Import | ast.ImportFrom) -> tuple[str, tuple[tuple[str, str | None], ...]]:
    names = tuple((alias.name, alias.asname) for alias in node.names)
    if isinstance(node, ast.Import):
        return "import", names
    return f"from:{node.level}:{node.module}", names


_IDENTIFIER_AST_FIELDS = {
    "arg",
    "asname",
    "attr",
    "id",
    "module",
    "name",
    "names",
}


def _canonical_structure_value(value: object, *, field: str = "") -> object:
    """Return a Python-minor-neutral structural AST record.

    Identifier-bearing strings remain exact. Literal values are represented by
    their exact built-in type only, so the digest table does not hash itself.
    Empty/default fields introduced by newer Python AST versions are omitted.
    """

    if isinstance(value, ast.AST):
        fields = []
        for name, child in ast.iter_fields(value):
            canonical = _canonical_structure_value(child, field=name)
            if canonical is None or canonical == () or canonical == []:
                continue
            fields.append((name, canonical))
        return (type(value).__name__, tuple(fields))
    if type(value) is list:
        return tuple(_canonical_structure_value(item, field=field) for item in value)
    if type(value) is tuple:
        return tuple(_canonical_structure_value(item, field=field) for item in value)
    if type(value) is str:
        return value if field in _IDENTIFIER_AST_FIELDS else ("literal", "str")
    if value is None:
        return None
    if type(value) in {bool, int, float, complex, bytes}:
        return ("literal", type(value).__name__)
    return ("literal", type(value).__name__)


def _source_structure_record(text: str) -> tuple[object, ...]:
    tree = ast.parse(text)
    imports = tuple(
        _import_signature(node) for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
    )
    calls = tuple(
        _canonical_structure_value(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call)
    )
    attributes = tuple(
        _canonical_structure_value(node) for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    )
    loaded_names = tuple(
        node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    )
    return (
        "closed_python_ast_capability_inventory_v1",
        _canonical_structure_value(tree),
        imports,
        calls,
        attributes,
        loaded_names,
    )


def _source_structure_sha256(text: str) -> str:
    return hashlib.sha256(repr(_source_structure_record(text)).encode("utf-8")).hexdigest()


def _structure_aggregate_sha256(records: tuple[tuple[str, str], ...], model_sha256: str) -> str:
    payload = ("closed_source_structure_aggregate_v1", records, model_sha256)
    return hashlib.sha256(repr(payload).encode("ascii")).hexdigest()


def _reviewed_lazy_producer_import(
    node: ast.ImportFrom,
    parents: tuple[ast.AST, ...],
    *,
    relative: str,
) -> bool:
    enclosing = [item for item in parents if isinstance(item, ast.FunctionDef)]
    classes = [item for item in parents if isinstance(item, ast.ClassDef)]
    names = tuple((alias.name, alias.asname) for alias in node.names)
    expected = {
        "experiments.loop_flux_counting_curvature_proof.counting_lane": (
            ("_direct_response_curl_record", None),
            ("_fcs_normal_connection_jet_record", None),
        ),
        "experiments.loop_flux_counting_curvature_proof.generator": (("build_branch_bundle", None),),
    }
    return (
        relative == "broker.py"
        and len(enclosing) == 1
        and enclosing[0].name == "_execute_reviewed_phase_child"
        and len(classes) == 0
        and node.level == 0
        and node.module in expected
        and names == expected[node.module]
    )


def _ancestors(tree: ast.AST) -> dict[ast.AST, tuple[ast.AST, ...]]:
    result: dict[ast.AST, tuple[ast.AST, ...]] = {}

    def visit(node: ast.AST, parents: tuple[ast.AST, ...]) -> None:
        result[node] = parents
        for child in ast.iter_child_nodes(node):
            visit(child, (*parents, node))

    visit(tree, ())
    return result


def _nearest_statement(node: ast.AST, parents: tuple[ast.AST, ...]) -> ast.stmt | None:
    if isinstance(node, ast.stmt):
        return node
    return next((item for item in reversed(parents) if isinstance(item, ast.stmt)), None)


def _statement_sha256(node: ast.AST, parents: tuple[ast.AST, ...]) -> str | None:
    statement = _nearest_statement(node, parents)
    if statement is None:
        return None
    return hashlib.sha256(ast.unparse(statement).encode("utf-8")).hexdigest()


def _reviewed_path_statement(
    node: ast.AST,
    parents: tuple[ast.AST, ...],
    *,
    role: str,
    relative: str,
) -> bool:
    digest = _statement_sha256(node, parents)
    return digest is not None and digest in _REVIEWED_PATH_STATEMENT_SHA256.get((role, relative), frozenset())


def _reviewed_capability_statement(
    node: ast.AST,
    parents: tuple[ast.AST, ...],
    *,
    role: str,
    relative: str,
) -> bool:
    digest = _statement_sha256(node, parents)
    return digest is not None and digest in _REVIEWED_CAPABILITY_STATEMENT_SHA256.get(
        (role, relative), frozenset()
    )


def analyze_source_text(text: str, *, role: str, relative: str) -> tuple[str, ...]:
    if role not in ROLE_FILES or type(text) is not str or type(relative) is not str:
        return ("unreviewed_role_or_source",)
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return ("syntax_error",)
    parents = _ancestors(tree)
    issues: list[str] = []
    observed_structure = _source_structure_sha256(text)
    if _REVIEWED_SOURCE_STRUCTURE_SHA256.get(relative) == observed_structure:
        return ()
    issues.append(f"unreviewed_source_structure:{relative}")
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import) and any(alias.name == "pathlib" for alias in node.names):
                issues.append("unreviewed_pathlib_import")
            if isinstance(node, ast.ImportFrom):
                imported = tuple((alias.name, alias.asname) for alias in node.names)
                expected_pathlib = _REVIEWED_PATHLIB_IMPORTS.get((role, relative))
                if node.module == "pathlib" and (node.level != 0 or imported != expected_pathlib):
                    issues.append("unreviewed_pathlib_import")
                if node.module != "pathlib" and any(
                    alias.name in _PATH_CONSTRUCTORS or alias.asname in _PATH_CONSTRUCTORS
                    for alias in node.names
                ):
                    issues.append("path_constructor_reexport")
            for module in _import_name(node):
                root = module.split(".", 1)[0]
                if root in _CONTROLLED_MODULE_ROOTS and _import_signature(
                    node
                ) not in _REVIEWED_CAPABILITY_IMPORTS.get((role, relative), frozenset()):
                    issues.append(f"forbidden_capability_import:{module}")
                if module.startswith(PREDICTOR_PACKAGE) and role != "geometry":
                    issues.append(f"predictor_import_outside_geometry:{module}")
                if role == "broker" and module.startswith(f"{CURRENT_PACKAGE}.geometry_plan"):
                    issues.append(f"broker_imported_geometry_lane:{module}")
                if module.startswith(PRODUCER_PACKAGE):
                    if not (
                        role == "broker"
                        and isinstance(node, ast.ImportFrom)
                        and _reviewed_lazy_producer_import(
                            node,
                            parents[node],
                            relative=relative,
                        )
                    ):
                        issues.append(f"producer_import_outside_lazy_broker:{module}")
        if isinstance(node, ast.Name) and node.id in _DYNAMIC_CAPABILITIES:
            if not (role == "anchor" and node.id == "compile"):
                issues.append(f"dynamic_capability_reference:{node.id}")
        if (
            isinstance(node, ast.Name)
            and node.id in _CONTROLLED_MODULE_ROOTS
            and not _reviewed_capability_statement(
                node,
                parents[node],
                role=role,
                relative=relative,
            )
        ):
            issues.append(f"controlled_module_capability:{node.id}")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            allowed_dunders = {
                "anchor": {
                    "__annotations__",
                    "__builtins__",
                    "__closure__",
                    "__code__",
                    "__defaults__",
                    "__dict__",
                    "__file__",
                    "__globals__",
                    "__kwdefaults__",
                    "__loader__",
                    "__module__",
                    "__name__",
                    "__package__",
                    "__qualname__",
                    "__spec__",
                },
                "broker": {"__setattr__"},
                "support": {"__name__"},
                "protocol": {
                    "__setattr__",
                    "__plan",
                    "__state",
                    "__source_lock",
                    "__fit",
                    "__predictions",
                    "__calibration_responses",
                    "__degeneracy",
                },
                "focused_test": {
                    "__annotations__",
                    "__builtins__",
                    "__closure__",
                    "__code__",
                    "__defaults__",
                    "__dict__",
                    "__kwdefaults__",
                    "__module__",
                    "__name__",
                    "__qualname__",
                    "__setattr__",
                    "__state",
                },
            }
            if node.attr not in allowed_dunders.get(role, set()):
                issues.append(f"dunder_attribute:{node.attr}")
        if (
            isinstance(node, ast.Attribute)
            and node.attr in (_PATH_CAPABILITY_ATTRIBUTES | _PATH_CONSTRUCTORS)
            and not _reviewed_path_statement(
                node,
                parents[node],
                role=role,
                relative=relative,
            )
        ):
            issues.append(f"path_or_io_capability:{node.attr}")
        if isinstance(node, ast.Call):
            constructor = None
            if isinstance(node.func, ast.Name) and node.func.id in _PATH_CONSTRUCTORS:
                constructor = node.func.id
            elif isinstance(node.func, ast.Attribute) and node.func.attr in _PATH_CONSTRUCTORS:
                constructor = node.func.attr
            if constructor is not None and not _reviewed_path_statement(
                node,
                parents[node],
                role=role,
                relative=relative,
            ):
                issues.append(f"path_constructor_capability:{constructor}")
    if role == "broker":
        forbidden_names = {"GeometryPlan", "PredictionCommit", "coefficients", "connection_basis"}
        used = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        for name in sorted(forbidden_names & used):
            issues.append(f"broker_received_geometry_or_prediction:{name}")
    if role == "geometry":
        imported = {
            module
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for module in _import_name(node)
        }
        if any(module.startswith(PRODUCER_PACKAGE) for module in imported):
            issues.append("geometry_received_producer_capability")
    if role == "fit" and PRODUCER_PACKAGE in text:
        issues.append("fit_mentions_producer_package")
    return tuple(sorted(set(issues)))


def source_firewall_record() -> dict[str, object]:
    package_entries = tuple(sorted(path.name for path in PACKAGE_DIR.iterdir()))
    expected_entries = EXPECTED_PACKAGE_FILES
    unexpected = tuple(name for name in package_entries if name not in expected_entries)
    missing = tuple(name for name in expected_entries if name not in package_entries)
    records = []
    for role, relative, kind in MATERIAL_FILES:
        path = SIM_ROOT / relative if "/" in relative else PACKAGE_DIR / relative
        if not path.is_file() or _has_reparse(path):
            records.append(
                {
                    "role": role,
                    "relative": relative,
                    "raw_sha256": None,
                    "issues": ("missing_or_linked_material",),
                }
            )
            continue
        with path.open("rb") as stream:
            raw = stream.read()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            issues = ("non_utf8_source",)
        else:
            issues = analyze_source_text(text, role=role, relative=relative) if kind == "python" else ()
        structure_sha256 = _source_structure_sha256(text) if kind == "python" and not issues else None
        records.append(
            {
                "role": role,
                "relative": relative,
                "raw_sha256": hashlib.sha256(raw).hexdigest(),
                "source_structure_sha256": structure_sha256,
                "issues": issues,
            }
        )
    structure_records = tuple(
        (record["relative"], record["source_structure_sha256"])
        for record in records
        if record["source_structure_sha256"] is not None
    )
    model_record = next(record for record in records if record["relative"] == "MODEL_CONTRACT.md")
    structure_aggregate = _structure_aggregate_sha256(
        structure_records,
        model_record["raw_sha256"],
    )
    return {
        "authority": "defense_in_depth_static_lane_partition",
        "role_files": tuple((role, files) for role, files in ROLE_FILES.items()),
        "material_files": MATERIAL_FILES,
        "file_records": tuple(records),
        "expected_package_files": EXPECTED_PACKAGE_FILES,
        "unexpected_package_entries": unexpected,
        "missing_package_entries": missing,
        "reviewed_model_contract_sha256": _REVIEWED_MODEL_CONTRACT_SHA256,
        "source_structure_aggregate_sha256": structure_aggregate,
        "protected_role_firewalls_clean": not unexpected
        and not missing
        and model_record["raw_sha256"] == _REVIEWED_MODEL_CONTRACT_SHA256
        and structure_aggregate == _REVIEWED_STRUCTURE_AGGREGATE_SHA256
        and all(not record["issues"] for record in records),
        "producer_import_permitted_only_in_lazy_broker": True,
        "predictor_import_permitted_only_in_geometry_lane": True,
        "bytecode_cache_policy": "python_-B_required_any_package_directory_refuses",
        "source_structure_authority": (
            "defense_in_depth_only_external_git_source_lock_is_publication_authority"
        ),
    }
