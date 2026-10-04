def sift(description):
    prompt = """
你正在做PCB图像标注，任务是识别所给的图像，对图像质量进行分级以及判断是否可用。

判定细则：
1. `is_real_pcb` 是否是真实PCB图像，而不是无关图、CG图、商品图或包装图。
2. `is_match_description` PCB是否大致符合以下描述：
%s
3. `condition` 为图片质量做出分级：
- high： 图像清晰完整，丝印文字能够识别
- medium： 有轻微模糊、曝光、或角度，特征能够识别，但文字无法识别
- low： 图像不完整或物体有遮挡，模糊、曝光、或角度问题导致部分特征无法识别
- unusable： 模糊、曝光、角度或遮挡严重，或者多pcb无序摆放，图像不可用
4. `is_multi_pcb` 图像是否不只一个pcb板，但图像本身清晰，可通过裁剪使用
5. `usable` 当is_real_pcb、is_match_description 为 false，condition 为 unusable时，后面的可不用判定而为null，usable 设为 false

按以下json格式输出
{
    "is_real_pcb":"bool",
    "is_match_description":"bool",
    "condition":"high|medium|low|unusable",
    "is_multi_pcb":"bool",
    "usable":"bool"
}
""" % (description)
    return prompt

def classify(description):
    prompt = """
你正在做PCB图像标注，任务是识别所给的图像以及对应的图像描述，对图像进行多特征的分类。
图像描述如下：
%s

细则：
1. `name` 描述中的pcb名称，没有则为null
2. `model` 描述中的pcb型号，没有则为null
3. `type` 按功能源头对pcb进行分类(需要与描述对应)：
- computing 计算类(如主板、显卡、内存条、网卡、硬盘)
- communication 通信类(如手机主板、路由器板、基站板、交换机板)
- industrial_control 工业控制类(如PLC板、伺服驱动板、变频器板、仪器仪表)
- power_supply 电源类(如开关电源板、UPS电源板、充电器板)
- display 显示/音视频类(如电视主板、音响功放板、DVD/VCD播放器板、摄像机板)
- household 家电类(如洗衣机控制板、空调控制板、微波炉板、电饭煲板)
- chip 仅芯片带板料
- others 其他
- null 描述中不能体现
4. `completeness` 按完整度对pcb进行分类：
- complete 完整板：元件齐全，可能整体复用
- medium 部分拆解板：部分元件已拆除
- incomplete 残板：仅剩PCB基材和少量元件
5. `component_density` pcb元件的密度，大致判断为 sparse稀疏|medium中等|dense密集 即可
按以下json格式输出
{
    "name":"str|null",
    "model":"str|null",
    "type":"str|null",
    "completeness":"str",
    "component_density":"str"
}
    """ % (description)
    return prompt

def value(image_info):
    prompt = f"""
    
    """
    return prompt